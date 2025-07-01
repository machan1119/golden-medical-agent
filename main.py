from fastapi import FastAPI
from routers import sms, gmail, store, chat
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Multi-Channel Intake System",
    description="A sophisticated multi-channel intake system for healthcare processing",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sms.router, prefix="/sms", tags=["sms"])
app.include_router(gmail.router, prefix="/gmail", tags=["gmail"])
app.include_router(store.router, prefix="/store", tags=["store"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True)
