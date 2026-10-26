from fastapi import FastAPI

from app.routers.candidates import router as candidates_router

app = FastAPI(title="TechForce", version="0.1.0")
app.include_router(candidates_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
