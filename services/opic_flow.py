# services/opic_flow.py
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import UserProfile, OpicSession
from models import OpicTurn as OpicTurnModel  # ✅ ORM Turn 모델은 이걸로만 사용

from services.examiner import generate_next_question
from services.rater import rate_session
from sqlalchemy.exc import IntegrityError

# ----------------------------
# DB helpers
# ----------------------------
def create_profile(db: Session, profile: dict) -> int:
    name = profile["name"]
    job = profile["job"]  # job nullable=False 기준

    # 1️⃣ 먼저 기존 프로필 조회
    existing = (
        db.query(UserProfile)
        .filter(UserProfile.name == name, UserProfile.job == job)
        .first()
    )

    if existing:
        return existing.profile_id

    # 2️⃣ 없으면 새로 생성
    hobbies = profile.get("hobbies", [])

    db_obj = UserProfile(
        name=name,
        job=job,
        city=profile.get("city"),
        hobbies_json=json.dumps(hobbies, ensure_ascii=False),
        speaking_style=profile.get("speaking_style"),
    )

    db.add(db_obj)

    try:
        db.commit()
        db.refresh(db_obj)
        return db_obj.profile_id

    except IntegrityError:
        # 🔒 동시성 대비 (거의 실서비스용 안전장치)
        db.rollback()
        existing = (
            db.query(UserProfile)
            .filter(UserProfile.name == name, UserProfile.job == job)
            .first()
        )
        if existing:
            return existing.profile_id
        raise


def create_session(db: Session, profile_id: int, goal_grade: str, target_count: int = 12) -> int:
    db_obj = OpicSession(
        # session_id는 DB에서 자동 생성 (AI)
        profile_id=profile_id,
        goal_grade=goal_grade,
        target_count=target_count,
        status="RUNNING",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)  
    return db_obj.session_id



def save_turn(db: Session, session_id: int, role: str, text: str) -> None:
    # ✅ ORM 모델로 저장
    db.add(OpicTurnModel(session_id=session_id, role=role, text=text))
    db.commit()


def get_turns(db: Session, session_id: int) -> List[OpicTurnModel]:
    q = (
        db.query(OpicTurnModel)
        .filter(OpicTurnModel.session_id == session_id)
    )

    # ✅ created_at 있으면 그걸로, 없으면 id로 정렬(안전장치)
    if hasattr(OpicTurnModel, "created_at"):
        q = q.order_by(OpicTurnModel.created_at.asc())
    else:
        q = q.order_by(OpicTurnModel.id.asc())

    return q.all()


def _count_user_answers(db: Session, session_id: int) -> int:
    return (
        db.query(func.count(OpicTurnModel.id))
        .filter(OpicTurnModel.session_id == session_id, OpicTurnModel.role == "USER")
        .scalar()
        or 0
    )


def _get_profile_dict(db: Session, profile_id: int) -> Dict[str, Any]:
    prof = db.query(UserProfile).filter(UserProfile.profile_id == profile_id).first()
    if not prof:
        raise ValueError("profile not found")

    try:
        hobbies = json.loads(prof.hobbies_json) if prof.hobbies_json else []
    except Exception:
        hobbies = []

    return {
        "name": prof.name,
        "job": prof.job,
        "city": prof.city,
        "hobbies": hobbies,
        "speaking_style": getattr(prof, "speaking_style", None),
    }


# ----------------------------
# Session UX helpers
# ----------------------------
def seed_first_question(db: Session, session_id: int) -> Dict[str, Any]:
    """
    세션 시작 직후(사용자 답변 전에) 첫 질문을 생성/저장.
    /api/opic/sessions 응답에서 firstQuestion으로 내려주기 좋음.
    """
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    if not sess:
        raise ValueError("session not found")

    profile = _get_profile_dict(db, sess.profile_id)

    first_q = generate_next_question(
        profile=profile,
        goal_grade=sess.goal_grade,
        history=[],
        last_user_answer=None,
        is_first=True,
    )

    save_turn(db, session_id, "EXAMINER", first_q)
    return {"sessionId": session_id, "questionText": first_q, "turnIndex": 0}


def get_session_summary(db: Session, session_id: int) -> Dict[str, Any]:
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    if not sess:
        raise ValueError("session not found")

    answered = _count_user_answers(db, session_id)
    target = getattr(sess, "target_count", None) or 12
    status = getattr(sess, "status", "RUNNING")

    return {
        "sessionId": session_id,
        "status": status,
        "answered": answered,
        "targetCount": target,
        "goalGrade": sess.goal_grade,
        "profileId": sess.profile_id,
    }


# ----------------------------
# Role A: Examiner (질문 생성)
# ----------------------------
def run_examiner_turn(db: Session, session_id: str, user_input: str) -> Dict[str, Any]:
    """
    사용자의 답변을 저장하고,
    그 답변 기반으로 Examiner가 '다음 질문 1개'만 생성하여 반환/저장.
    """
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    if not sess:
        raise ValueError("session not found")

    profile = _get_profile_dict(db, sess.profile_id)

    turns = get_turns(db, session_id)

    last_examiner_q = None
    for t in reversed(turns):
        if t.role == "EXAMINER":
            last_examiner_q = t.text
            break

    if not last_examiner_q:
        seeded = seed_first_question(db, session_id)
        last_examiner_q = seeded["questionText"]

    # 사용자 답변 저장
    save_turn(db, session_id, "USER", user_input)

    # 최신 N턴만 history로 전달
    history = [{"role": t.role, "text": t.text} for t in turns[-12:]] + [{"role": "USER", "text": user_input}]

    next_q = generate_next_question(
        profile=profile,
        goal_grade=sess.goal_grade,
        history=history,
        last_user_answer=user_input,
        is_first=False,
    )

    save_turn(db, session_id, "EXAMINER", next_q)

    turn_index = _count_user_answers(db, session_id)

    return {
        "sessionId": session_id,
        "questionText": next_q,
        "turnIndex": turn_index,
    }


# ----------------------------
# Role B: Rater (JSON 평가)
# ----------------------------
def end_and_rate_session(db: Session, session_id: str, force: bool = False) -> dict:
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    if not sess:
        raise ValueError("session not found")

    # ✅ 멱등 처리
    if sess.status == "ENDED" and sess.report_json:
        return json.loads(sess.report_json)

    turns = get_turns(db, session_id)
    answered = _count_user_answers(db, session_id)
    target = sess.target_count or 12

    if not force and answered < min(3, target):
        raise ValueError(f"not enough answers to rate: {answered}")

    profile = _get_profile_dict(db, sess.profile_id)
    transcript = [{"role": t.role, "text": t.text} for t in turns]

    report_json = rate_session(
        profile=profile,
        goal_grade=sess.goal_grade,
        target_count=target,
        transcript=transcript,
    )

    sess.status = "ENDED"
    sess.ended_at = datetime.utcnow()
    sess.report_json = json.dumps(report_json, ensure_ascii=False)

    db.commit()
    return report_json
