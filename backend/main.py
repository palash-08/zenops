from fastapi import FastAPI

app = FastAPI(title="ZenOps Backend")


@app.get("/")
async def root():
    return {"message": "ZenOps Backend is running"}