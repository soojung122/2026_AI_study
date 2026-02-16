# main.py
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import engine
from models import Base
from routers.opic import router as opic_router

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # ✅ 실행 시 테이블 자동 생성 (MVP)
    Base.metadata.create_all(bind=engine)

@app.get("/api/health")
def health():
    return {"ok": True}

app.include_router(opic_router)
