from pydantic import BaseModel, EmailStr, Field
# FastAPI에서 데이터 검증하는 라이브러리

class RegisterRequest(BaseModel):   # 회원가입 요청
    email: EmailStr   # 이메일 형식만 가능
    password: str = Field(min_length=8, max_length=64)  # 비밀번호 길이 제한
    name: str | None = Field(default=None, max_length=100) # 이름은 선택사항임, 길이 제

class LoginRequest(BaseModel): # 로그인 요청
    email: EmailStr
    password: str

class TokenResponse(BaseModel): # 로그인 성공 응답
    access_token: str
    token_type: str = "bearer"    # JWT 토큰 타입

class MeResponse(BaseModel): # 사용자 정보 응답 = 사용자 정보 조회
    id: int
    email: EmailStr
    name: str | None = None
