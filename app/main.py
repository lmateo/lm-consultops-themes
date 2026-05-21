from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import Base, engine
from app.routers import admin, public

settings = get_settings()
app = FastAPI(title=settings.app_name)

Base.metadata.create_all(bind=engine)

project_root = Path(__file__).resolve().parent.parent
static_dir = Path(__file__).resolve().parent / "static"
crafto_dir = project_root / "crafto-html-templates"

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
if crafto_dir.is_dir():
    app.mount("/crafto", StaticFiles(directory=str(crafto_dir)), name="crafto")

app.include_router(public.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
