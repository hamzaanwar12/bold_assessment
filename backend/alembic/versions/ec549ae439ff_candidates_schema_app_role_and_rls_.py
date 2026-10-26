"""candidates schema, app role, and RLS policy

Schema and authorization model version together because they are
inseparable -- see docs/adr/0002 and spec.md ("Schema" / "Authorization").

Non-negotiables this revision encodes:

- `techforce_app` is a dedicated, non-owner role. It gets DML grants only;
  the owner connection (`techforce`, the migration role) keeps ownership.
  RLS does not apply to a table's owner or a superuser, so if the API ever
  connects as the owner the policy still exists but protects nothing.
- `candidates` carries both `ENABLE ROW LEVEL SECURITY` and
  `FORCE ROW LEVEL SECURITY` -- two independent guards against that trap.
- The policy resolves Assigned Regions itself from `recruiter_regions` /
  `recruiters.is_admin`, keyed on a session setting (`app.recruiter_id`)
  holding only a Recruiter identifier. The caller never supplies a region
  list.
- `recruiters` and `recruiter_regions` stay readable by `techforce_app`, or
  the policy's own lookup fails closed.

Revision ID: ec549ae439ff
Revises:
Create Date: 2026-10-26 22:08:49.718129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec549ae439ff'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REGION_CODES = ("US-MW", "US-NE", "US-SE", "US-W", "PH-MNL", "CO-BOG")
CANDIDATE_STATUSES = ("active", "screening", "interviewing", "withdrawn")


def upgrade() -> None:
    op.create_table(
        "recruiters",
        sa.Column("recruiter_id", sa.Text(), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "recruiter_regions",
        sa.Column(
            "recruiter_id",
            sa.Text(),
            sa.ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("region_code", sa.Text(), primary_key=True),
        sa.CheckConstraint(
            f"region_code IN {REGION_CODES!r}",
            name="ck_recruiter_regions_region_code",
        ),
    )
    op.create_index(
        "ix_recruiter_regions_recruiter_id_region_code",
        "recruiter_regions",
        ["recruiter_id", "region_code"],
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("legacy_candidate_id", sa.Text(), nullable=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("region_code", sa.Text(), nullable=False),
        sa.Column("desired_role", sa.Text(), nullable=False),
        sa.Column("salary_expectation", sa.Numeric(), nullable=True),
        sa.Column("applied_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            f"region_code IN {REGION_CODES!r}",
            name="ck_candidates_region_code",
        ),
        sa.CheckConstraint(
            f"status IN {CANDIDATE_STATUSES!r}",
            name="ck_candidates_status",
        ),
    )
    op.create_index("ix_candidates_region_code", "candidates", ["region_code"])
    op.create_index("ix_candidates_status", "candidates", ["status"])

    # -- Application role -------------------------------------------------
    # Dedicated, non-owner role. The migration connection (the owner role)
    # keeps table ownership; techforce_app gets DML only. This is one of
    # the two independent guards against the owner-bypass trap -- see
    # docs/adr/0002.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'techforce_app') THEN
                CREATE ROLE techforce_app LOGIN PASSWORD 'techforce_app';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO techforce_app', current_database());
        END
        $$;
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON candidates TO techforce_app"
    )
    op.execute("GRANT USAGE, SELECT ON SEQUENCE candidates_id_seq TO techforce_app")
    # recruiters / recruiter_regions must stay readable by techforce_app, or
    # the policy's own lookup fails closed.
    op.execute("GRANT SELECT ON recruiters TO techforce_app")
    op.execute("GRANT SELECT ON recruiter_regions TO techforce_app")

    # -- Row-Level Security -------------------------------------------------
    op.execute("ALTER TABLE candidates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE candidates FORCE ROW LEVEL SECURITY")

    # The policy resolves Assigned Regions itself from recruiter_regions /
    # recruiters.is_admin, keyed on app.recruiter_id -- a Recruiter
    # identifier only. It never trusts a region list from the caller.
    # app.recruiter_id is set per-request via set_config(name, value, true)
    # (the "true" argument makes it transaction-local, i.e. SET LOCAL),
    # which is the parameterizable form -- never string-interpolated into a
    # SET statement.
    op.execute(
        """
        CREATE POLICY candidates_region_scope ON candidates
        USING (
            EXISTS (
                SELECT 1 FROM recruiters r
                WHERE r.recruiter_id = current_setting('app.recruiter_id', true)
                  AND r.is_admin
            )
            OR EXISTS (
                SELECT 1 FROM recruiter_regions rr
                WHERE rr.recruiter_id = current_setting('app.recruiter_id', true)
                  AND rr.region_code = candidates.region_code
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS candidates_region_scope ON candidates")
    op.execute("REVOKE SELECT ON recruiter_regions FROM techforce_app")
    op.execute("REVOKE SELECT ON recruiters FROM techforce_app")
    op.execute("REVOKE ALL ON SEQUENCE candidates_id_seq FROM techforce_app")
    op.execute("REVOKE ALL ON candidates FROM techforce_app")
    op.drop_index("ix_candidates_status", table_name="candidates")
    op.drop_index("ix_candidates_region_code", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index(
        "ix_recruiter_regions_recruiter_id_region_code",
        table_name="recruiter_regions",
    )
    op.drop_table("recruiter_regions")
    op.drop_table("recruiters")
    # The role is left in place deliberately: dropping it on every
    # downgrade would race other sessions holding it open, and migrating
    # back up re-grants cleanly either way (CREATE ROLE is idempotent via
    # the guard above).
