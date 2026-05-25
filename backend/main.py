from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import insights, actions

load_dotenv()

app = FastAPI(title="Churn Prevention API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router, prefix="/api")
app.include_router(actions.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
