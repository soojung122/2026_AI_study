import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt, JWTError

load_dotenv()  # 환경변수를 가져오기 위함

# .env 파일 경로 명시
load_dotenv(dotenv_path=".env")

# bcrypt 이 방식으로 암호화 설정(준비 과정)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT_SECRET 반드시 존재해야 함 (.env 없으면 에러 발생)
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = os.getenv("JWT_ALG", "HS256") # 암호화 알고리즘
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")) # 토큰 만료 시간

def hash_password(password: str) -> str:   # 비밀번호 암호화
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool: # 로그인 시 비밀번호 확인을 위
    return pwd_context.verify(password, hashed)

def create_access_token(subject: str) -> str:  # JWT 토큰 생성
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,  # 사용자 식별 정보
        "iat": int(now.timestamp()), # 토큰 생성 시간
        "exp": int((now + timedelta(minutes=EXPIRE_MIN)).timestamp()), # 토큰 만료 시간
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict: # JWT 토큰 검증 및 내용 읽기
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise ValueError("Invalid token")
