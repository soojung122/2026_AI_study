# main.py
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 260221 서은 추가 라이브러리
from fastapi import Depends, HTTPException  # API 생성, 의존성 주입, 에러 응답 처
# ❌ main.py에서는 토큰 파싱/HTTPBearer를 직접 쓰지 않도록 deps.py로 분리함
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # 요청 헤더의 토큰을 받기 위함
from sqlalchemy.orm import Session  # DB 세션을 이용하기 위함

from db import engine
from models import Base
from routers.opic import router as opic_router

# 260221 서은 추가 작성한 모듈 가져오기
from db import engine, get_db  # ORM 베이스, DB 연결 엔진, 세션 의존성
from models import User  # User (users 테이블 ORM 모델)
from schemas import RegisterRequest, LoginRequest, TokenResponse, MeResponse  # 요청/응답 Pydantic 모델들
from security import (
    hash_password,
    verify_password,
    create_access_token,
    # ❌ decode_token은 get_current_user에서만 쓰므로 deps.py로 이동
    # decode_token
)  # 비번 해시/검증, 토큰 생성/검증

# ✅ 260222 서은 - 현재 로그인 사용자 의존성 함수는 deps.py로 분리해서 import
from deps import get_current_user

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

# 260217 서은 - 로그인 api 추가
# 개발용: 모델 기반으로 테이블 생성 - DB에 테이블이 없으면 테이블 생성
# ✅ 중복 실행 방지를 위해 startup에서만 생성하도록 권장
# Base.metadata.create_all(bind=engine)

# ❌ bearer / get_current_user는 deps.py로 이동
# bearer = HTTPBearer(auto_error=False)

# 회원가입 API
@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # 1) 이메일 중복 확인
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    # 2) 비번 해시해서 저장
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()  # 실제 DB에 저장
    db.refresh(user)  # 다시 정보를 가져옴

    return {"id": user.id, "email": user.email, "name": user.name}  # 반환할 때 비밀번호는 가져오지 않음

# 로그인 API
@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # 1) 이메일로 유저 찾기
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # 2) 비밀번호 검증
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # 3) JWT 발급
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)

# ❌ 현재 로그인 사용자 정보를 가져오는 get_current_user는 deps.py로 이동
# def get_current_user(...): ...

# 내 정보 조회
@app.get("/api/auth/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email, name=user.name)