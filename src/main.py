import uvicorn


def run() -> None:
    uvicorn.run("iota_verbum_api.app:app", host="0.0.0.0", port=8000)
