"""POST /api/v1/candidates/import (ticket 06).

The Import endpoint: parse -> validate -> deduplicate in memory -> write
once, in that order, inside one request (spec.md: Import pipeline). A row
Rejection does not fail the request; a database error does, and rolls back
everything written so far in this Import.
"""

from __future__ import annotations

import csv
import io

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError

from app.dedup import deduplicate
from app.db import write_import
from app.deps import Recruiter, get_app_dsn, require_admin
from app.normalizers import NormalizationError
from app.schemas import Candidate, ImportReport, RejectedRow

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


def _rejection_reason(exc: ValidationError) -> str:
    """Prefer the human-readable reason carried by NormalizationError
    (app.normalizers) over Pydantic's generic wrapper message."""
    for error in exc.errors():
        cause = error.get("ctx", {}).get("error")
        if isinstance(cause, NormalizationError):
            return cause.reason
    errors = exc.errors()
    return errors[0]["msg"] if errors else "invalid row"


# A legacy export is a bounded artefact, not a stream. Cap it so an unbounded
# upload cannot exhaust memory, and answer 413 rather than dying.
MAX_UPLOAD_BYTES = 16 * 1024 * 1024


# Deliberately `def`, not `async def`: this handler does blocking work --
# psycopg I/O and CSV parsing. In an async handler that work runs ON the event
# loop and stalls every other request for the duration of the import. FastAPI
# runs a sync handler in a threadpool instead.
@router.post("/import", response_model=ImportReport)
def import_candidates(
    file: UploadFile = File(...),
    recruiter: Recruiter = Depends(require_admin),
    dsn: str = Depends(get_app_dsn),
) -> ImportReport:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="upload must be a .csv file")

    # Read one byte past the cap: if we get it, the upload is over the limit.
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB limit",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="upload is not valid UTF-8") from exc

    # csv.DictReader handles CRLF termination and quoted fields containing
    # embedded newlines correctly; splitting the text on "\n" ourselves
    # would corrupt any such row (spec.md: Import pipeline, phase 1).
    reader = csv.DictReader(io.StringIO(text))

    valid_rows: list[Candidate] = []
    rejected: list[RejectedRow] = []
    # 1-based, excluding the header (GLOSSARY.md: Source Row).
    for row_number, raw_row in enumerate(reader, start=1):
        try:
            valid_rows.append(Candidate.model_validate(raw_row))
        except ValidationError as exc:
            rejected.append(RejectedRow(row=row_number, reason=_rejection_reason(exc)))

    outcomes = deduplicate(valid_rows)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.transaction():
                imported, merged = write_import(conn, recruiter.recruiter_id, outcomes)
    except psycopg.Error as exc:
        # A database failure is a failed request: 5xx, nothing written.
        # psycopg's `with conn:` rolls back on exception before re-raising.
        raise HTTPException(
            status_code=500, detail="import failed; no Candidates were written"
        ) from exc

    return ImportReport(imported=imported, merged=merged, rejected=rejected)
