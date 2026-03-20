# routers/opic.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session


from db import SessionLocal
from services.opic_flow import (
    create_profile,
    create_session,
    seed_first_question,
    run_examiner_turn,
    end_and_rate_session,
    get_session_summary,
    _get_profile_dict,   # ✅ 추가
)


# ✅ 260222 서은 - 로그인 사용자 주입을 위해 추가
from deps import get_current_user
from models import User

router = APIRouter(prefix="/api/opic", tags=["opic"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Schemas ----------


class ProfileIn(BaseModel):
    name: str
    job: str
    city: Optional[str] = None
    hobbies: Dict[str, Any] = Field(default_factory=dict)
    speaking_style: Optional[str] = None


class SessionStartRequest(BaseModel):
    goalGrade: str = Field(..., examples=["IH"])
    targetCount: int = Field(12, ge=1, le=20)


class SessionStartResponse(BaseModel):
    sessionId: int
    profileId: int
    goalGrade: str
    targetCount: int
    firstQuestion: str
    turnIndex: int


class TurnRequest(BaseModel):
    userInput: str


class TurnResponse(BaseModel):
    sessionId: int
    questionText: str
    turnIndex: int


class EndSessionRequest(BaseModel):
    force: bool = False


class ReportResponse(BaseModel):
    sessionId: int
    report: Dict[str, Any]


# ---------- Session Endpoints ----------
@router.post("/sessions", response_model=SessionStartResponse)
def start_session(
    req: SessionStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile_id = user.id

    try:
        _get_profile_dict(db, profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="프로필을 먼저 저장해주세요.")

    session_id = create_session(db, profile_id, req.goalGrade, target_count=req.targetCount)
    first = seed_first_question(db, session_id)

    return SessionStartResponse(
        sessionId=session_id,
        profileId=profile_id,
        goalGrade=req.goalGrade,
        targetCount=req.targetCount,
        firstQuestion=first["questionText"],
        turnIndex=first["turnIndex"],
    )


@router.post("/sessions/{session_id}/turn", response_model=TurnResponse)
def session_turn(
    session_id: int,
    req: TurnRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),  # ✅ 260222 서은 - 인증 필요
):
    """
    Role A: Examiner turn
    """
    if not req.userInput or not req.userInput.strip():
        raise HTTPException(status_code=400, detail="userInput은 비어 있을 수 없습니다.")

    try:
        result = run_examiner_turn(db, session_id=session_id, user_input=req.userInput)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Examiner turn failed: {str(e)}")

    return TurnResponse(**result)


@router.post("/sessions/{session_id}/end", response_model=ReportResponse)
def end_session(
    session_id: int,
    req: EndSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),  # ✅ 260222 서은 - 인증 필요
):
    """
    Role B: Rater end
    """
    try:
        report_json = end_and_rate_session(db, session_id=session_id, force=req.force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rater end failed: {str(e)}")

    return ReportResponse(sessionId=session_id, report=report_json)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),  # ✅ 260222 서은 - 인증 필요
):
    """
    진행률/상태 조회
    """
    try:
        summary = get_session_summary(db, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get session failed: {str(e)}")
    return summary


# ---------- Legacy Endpoint (기존 프론트 호환용) ----------
class LegacyTurnRequest(BaseModel):
    sessionId: Optional[int] = None
    profileId: Optional[int] = None
    profile: Optional[ProfileIn] = None
    goalGrade: str
    userInput: str
    targetCount: int = 12


class LegacyTurnResponse(BaseModel):
    sessionId: int
    questionText: str
    turnIndex: int
    profileId: int


@router.post("/turn", response_model=LegacyTurnResponse)
def opic_turn_legacy(
    req: LegacyTurnRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),  # ✅ 260222 서은 - 현재 로그인 사용자 주입
):
    """
    기존 /api/opic/turn 호출 유지:
    - sessionId 없으면 세션 생성
    - profileId 없으면 프로필 생성/재사용
    - 이후 examiner turn 수행
    """
    if not req.userInput or not req.userInput.strip():
        raise HTTPException(status_code=400, detail="userInput은 비어 있을 수 없습니다.")

    profile_id = user.id
    try:
        _get_profile_dict(db, profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="프로필을 먼저 저장해주세요.")

    session_id = req.sessionId
    if not session_id:
        session_id = create_session(db, user.id, req.goalGrade, target_count=req.targetCount)
        # 레거시에서도 첫 질문 seed를 원하면 여기서 호출 가능 (선택)
        # seed_first_question(db, session_id)

    result = run_examiner_turn(db, session_id=session_id, user_input=req.userInput)

    return LegacyTurnResponse(
        sessionId=session_id,
        profileId=profile_id,
        questionText=result["questionText"],
        turnIndex=result["turnIndex"],
    )

# 프로필 저장하기
@router.post("/profile")
def save_my_opic_profile(
    req: ProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        profile_id = create_profile(db, req.model_dump(), user_id=user.id)
        saved_profile = _get_profile_dict(db, profile_id)
        return {
            "profileId": profile_id,
            "profile": saved_profile,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile save failed: {str(e)}")

# ✅ prefix가 이미 /api/opic 이므로, /start는 이렇게 등록해야 함
@router.post("/start")
def start_opic(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        goal = payload["goalGrade"]
        target = payload.get("targetCount", 12)
    except Exception:
        raise HTTPException(status_code=400, detail="payload 형식이 올바르지 않습니다.")

    try:
        saved_profile = _get_profile_dict(db, user.id)
    except Exception:
        raise HTTPException(status_code=400, detail="프로필을 먼저 저장해주세요.")

    session_id = create_session(db, user.id, goal, target_count=target)
    first = seed_first_question(db, session_id)

    return {
        "profileId": user.id,
        "sessionId": session_id,
        "firstQuestion": first["questionText"],
        "turnIndex": first["turnIndex"],
        "profile": saved_profile,
    }

@router.get("/profile")
def get_my_opic_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        profile = _get_profile_dict(db, user.id)
        return {
            "profileId": user.id,
            "profile": profile,
        }
    except Exception:
        return {
            "profileId": user.id,
            "profile": None,
        }