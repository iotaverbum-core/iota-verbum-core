import uvicorn

from iota_verbum_api.app import app


def run() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
