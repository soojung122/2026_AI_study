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
)

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
    job: str  # ✅ UK(name, job) 기준이면 job은 필수로 받는 게 안전
    city: Optional[str] = None
    hobbies: List[str] = []
    speaking_style: Optional[str] = None


class SessionStartRequest(BaseModel):
    profileId: Optional[int] = None
    profile: Optional[ProfileIn] = None
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
def start_session(req: SessionStartRequest, db: Session = Depends(get_db)):
    """
    세션 시작:
    - profileId가 있으면 재사용
    - 없으면 profile(name/job/...)로 DB에서 get-or-create
    - 세션 생성 후 첫 질문 seed 해서 반환
    """
    profile_id = req.profileId
    profile_dict = req.profile.model_dump() if req.profile else None

    if not profile_id:
        if not profile_dict:
            raise HTTPException(status_code=400, detail="profileId 또는 profile이 필요합니다.")
        # job 필수 방어 (DB nullable=False면 꼭 필요)
        if not profile_dict.get("job"):
            raise HTTPException(status_code=400, detail="job은 필수입니다.")
        profile_id = create_profile(db, profile_dict)  # int 반환

    session_id = create_session(db, profile_id, req.goalGrade, target_count=req.targetCount)  # int 반환

    # ✅ 세션 시작 직후 첫 질문 생성/저장
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
def session_turn(session_id: int, req: TurnRequest, db: Session = Depends(get_db)):
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
def end_session(session_id: int, req: EndSessionRequest, db: Session = Depends(get_db)):
    """
    Role B: Rater end
    """
    try:
        report_json = end_and_rate_session(db, session_id=session_id, force=req.force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rater end failed: {str(e)}")

    return ReportResponse(sessionId=session_id, report=report_json)


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
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
def opic_turn_legacy(req: LegacyTurnRequest, db: Session = Depends(get_db)):
    """
    기존 /api/opic/turn 호출 유지:
    - sessionId 없으면 세션 생성
    - profileId 없으면 프로필 생성/재사용
    - 이후 examiner turn 수행
    """
    if not req.userInput or not req.userInput.strip():
        raise HTTPException(status_code=400, detail="userInput은 비어 있을 수 없습니다.")

    profile_id = req.profileId
    profile_dict = req.profile.model_dump() if req.profile else None

    if not profile_id:
        if not profile_dict:
            raise HTTPException(status_code=400, detail="profileId 또는 profile이 필요합니다.")
        if not profile_dict.get("job"):
            raise HTTPException(status_code=400, detail="job은 필수입니다.")
        profile_id = create_profile(db, profile_dict)

    session_id = req.sessionId
    if not session_id:
        session_id = create_session(db, profile_id, req.goalGrade, target_count=req.targetCount)
        # 레거시에서도 첫 질문 seed를 원하면 여기서 호출 가능 (선택)
        # seed_first_question(db, session_id)

    result = run_examiner_turn(db, session_id=session_id, user_input=req.userInput)

    return LegacyTurnResponse(
        sessionId=session_id,
        profileId=profile_id,
        questionText=result["questionText"],
        turnIndex=result["turnIndex"],
    )


# ✅ prefix가 이미 /api/opic 이므로, /start는 이렇게 등록해야 함
@router.post("/start")
def start_opic(payload: dict, db: Session = Depends(get_db)):
    """
    프론트에서 '저장/시작 버튼' 없이도 한 번에:
    - 프로필 get-or-create
    - 세션 생성
    - 첫 질문 seed
    """
    try:
        profile = payload["profile"]
        goal = payload["goalGrade"]
        target = payload.get("targetCount", 12)
    except Exception:
        raise HTTPException(status_code=400, detail="payload 형식이 올바르지 않습니다.")

    if not profile.get("name") or not profile.get("job"):
        raise HTTPException(status_code=400, detail="profile.name, profile.job은 필수입니다.")

    profile_id = create_profile(db, profile)
    session_id = create_session(db, profile_id, goal, target_count=target)
    first = seed_first_question(db, session_id)

    return {
        "profileId": profile_id,
        "sessionId": session_id,
        "firstQuestion": first["questionText"],
        "turnIndex": first["turnIndex"],
    }
