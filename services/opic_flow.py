# services/opic_flow.py
import json
from datetime import datetime
from typing import Dict, Any, List
import os
import random
from functools import lru_cache
import re


from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import UserProfile, OpicSession
from models import OpicTurn as OpicTurnModel  # ✅ ORM Turn 모델은 이걸로만 사용

from services.examiner import generate_next_question
from services.rater import rate_session



# ----------------------------
# DB helpers
# ----------------------------
def create_profile(db: Session, profile: dict, user_id: int) -> int:
    # ✅ 유저별 프로필 1개이므로 user_id로만 찾음
    existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    hobbies = profile.get("hobbies", [])

    if existing:
        # ✅ 이미 있으면 업데이트(원하면). "1개만" 유지
        existing.name = profile["name"]
        existing.job = profile["job"]
        existing.city = profile.get("city")
        existing.hobbies_json = json.dumps(hobbies, ensure_ascii=False)
        existing.speaking_style = profile.get("speaking_style")

        db.commit()
        return existing.user_id  # ✅ PK 반환

    # ✅ 없으면 생성
    db_obj = UserProfile(
        user_id=user_id,  # ✅ PK
        name=profile["name"],
        job=profile["job"],
        city=profile.get("city"),
        hobbies_json=json.dumps(hobbies, ensure_ascii=False),
        speaking_style=profile.get("speaking_style"),
    )
    db.add(db_obj)
    db.commit()
    return db_obj.user_id  # ✅ PK 반환


def create_session(db: Session, user_id: int, goal_grade: str, target_count: int = 12) -> int:
    db_obj = OpicSession(
        user_id=user_id,  # ✅ profile_id -> user_id
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
    q = db.query(OpicTurnModel).filter(OpicTurnModel.session_id == session_id)

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
    # ✅ profile_id 변수명은 유지해도 되지만, 실제 값은 user_id임
    prof = db.query(UserProfile).filter(UserProfile.user_id == profile_id).first()
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


TOPIC_ROOT = os.getenv("OPIC_TOPIC_DIR", "topic")

def _grade_dir(goal_grade: str) -> str:
    g = (goal_grade or "").upper().strip()
    return "IM" if g == "IM" else "IH_AL"

@lru_cache(maxsize=64)
def _list_bank_topics(goal_grade: str, mode: str) -> list[str]:
    """
    topic/{IM|IH_AL}/{mode} 폴더 안의 .txt 파일명을 스캔해서
    ["home", "cafe", ...] 형태로 반환
    """
    gdir = _grade_dir(goal_grade)
    m = (mode or "survey").lower().strip()
    folder = os.path.join(TOPIC_ROOT, gdir, m)

    if not os.path.isdir(folder):
        return []

    topics = []
    for fname in os.listdir(folder):
        if fname.lower().endswith(".txt"):
            stem = os.path.splitext(fname)[0].strip()
            if stem:
                topics.append(stem)

    topics.sort()
    return topics

def _topic_exists_in_bank(goal_grade: str, mode: str, topic_name: str) -> bool:
    topic = (topic_name or "").strip().lower()
    if not topic:
        return False
    return topic in set(_list_bank_topics(goal_grade, mode))

def _tokenize(s: str) -> set[str]:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9_ ]+", " ", s)
    return {t for t in s.split() if t}

def normalize_topic_to_bank(goal_grade: str, mode: str, raw_topic: str) -> tuple[str, bool]:
    """
    raw_topic을 해당 mode 폴더의 txt 파일명 중 하나로 매칭.
    return: (normalized_topic, matched_bool)
    """
    raw = (raw_topic or "").strip().lower()
    if not raw:
        return ("home", False)

    bank_topics = _list_bank_topics(goal_grade, mode)
    if not bank_topics:
        return (raw, False)

    # 1) 완전 일치
    if raw in bank_topics:
        return (raw, True)

    raw_tokens = _tokenize(raw)

    best = None
    best_score = 0

    for t in bank_topics:
        t_tokens = _tokenize(t)

        score = 0
        if raw in t or t in raw:
            score += 3
        score += len(raw_tokens & t_tokens)

        if score > best_score:
            best_score = score
            best = t

    if best is not None and best_score >= 1:
        return (best, True)

    return (raw, False)

def pick_survey_topic_from_profile_dict(profile: dict, goal_grade: str, min_n=2, max_n=3) -> str:
    """
    survey:
    - profile(job+hobbies)에서 후보를 만들고 2~3개 샘플링 후 1개 선택
    - 그 topic을 survey 은행 파일명으로 매칭 시도
    - ✅ 매칭 실패하면 sudden 은행에서 랜덤 topic으로 fallback
    """
    candidates = []

    job = (profile.get("job") or "").strip().lower()
    if job:
        candidates.append(job)

    hobbies = profile.get("hobbies") or []
    for h in hobbies:
        s = str(h).strip().lower()
        if s:
            candidates.append(s)

    candidates = list({c for c in candidates if c})
    if not candidates:
        return "home"

    n = random.randint(min_n, min(max_n, len(candidates)))
    subset = random.sample(candidates, n)
    chosen = random.choice(subset)

    normalized, matched = normalize_topic_to_bank(goal_grade, "survey", chosen)

    # ✅ 매칭 성공이면 그걸 사용
    if matched and _topic_exists_in_bank(goal_grade, "survey", normalized):
        return normalized

    # ✅ 매칭 실패면 sudden 은행에서 랜덤 topic
    return pick_sudden_topic_from_bank(goal_grade)


def pick_sudden_topic_from_bank(goal_grade: str) -> str:
    """
    sudden: profile에서 가져오지 않고, sudden 폴더의 txt 중 랜덤으로 선택
    """
    topics = _list_bank_topics(goal_grade, "sudden")
    return random.choice(topics) if topics else "home"

def decide_topic_name(profile: dict, goal_grade: str, mode: str) -> str:
    m = (mode or "survey").lower().strip()
    gdir = _grade_dir(goal_grade)

    if m == "survey":
        return pick_survey_topic_from_profile_dict(profile, goal_grade)

    if m == "sudden":
        topics = _list_bank_topics(goal_grade, "sudden")
        return random.choice(topics) if topics else "home"

    if m == "advance":
        # IM에는 advance 폴더가 없으니 survey 정책(=profile 기반)으로 처리
        if gdir == "IM":
            return pick_survey_topic_from_profile_dict(profile, goal_grade)

        topics = _list_bank_topics(goal_grade, "advance")
        return random.choice(topics) if topics else "home"

    return pick_survey_topic_from_profile_dict(profile, goal_grade)

# ----------------------------
# Session UX helpers
# ----------------------------
def seed_first_question(db: Session, session_id: int) -> Dict[str, Any]:

    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    if not sess:
        raise ValueError("session not found")

    profile = _get_profile_dict(db, sess.user_id)

    # ✅ 추가
    mode = getattr(sess, "mode", "survey")
    topic_name = decide_topic_name(profile, sess.goal_grade, mode)

    first_q = generate_next_question(
        profile=profile,
        goal_grade=sess.goal_grade,
        history=[],
        last_user_answer=None,
        is_first=True,
        topic_name=topic_name,
        mode=mode,
    )

    save_turn(db, session_id, "EXAMINER", first_q)

    return {
        "sessionId": session_id,
        "questionText": first_q,
        "turnIndex": 0,
    }


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
        # ❌ OpicSession에는 profile_id가 없음
        # "profileId": sess.profile_id,
        # ✅ 유저별 프로필 1개 구조에서는 profileId == user_id 로 내려도 됨(프론트 호환용)
        "profileId": sess.user_id,
    }


# ----------------------------
# Role A: Examiner (질문 생성)
# ----------------------------
def run_examiner_turn(db: Session, session_id: int, user_input: str) -> Dict[str, Any]:

    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    if not sess:
        raise ValueError("session not found")

    profile = _get_profile_dict(db, sess.user_id)

    # ✅ 추가 (핵심)
    mode = getattr(sess, "mode", "survey")
    topic_name = decide_topic_name(profile, sess.goal_grade, mode)

    turns = get_turns(db, session_id)

    last_examiner_q = None
    for t in reversed(turns):
        if t.role == "EXAMINER":
            last_examiner_q = t.text
            break

    if not last_examiner_q:
        seeded = seed_first_question(db, session_id)
        turns = get_turns(db, session_id)

    save_turn(db, session_id, "USER", user_input)

    history = (
        [{"role": t.role, "text": t.text} for t in turns[-12:]]
        + [{"role": "USER", "text": user_input}]
    )

    # ✅ topic_name, mode 전달
    next_q = generate_next_question(
        profile=profile,
        goal_grade=sess.goal_grade,
        history=history,
        last_user_answer=user_input,
        is_first=False,
        topic_name=topic_name,
        mode=mode,
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
def end_and_rate_session(db: Session, session_id: int, force: bool = False) -> dict:
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

    # ❌ OpicSession에는 profile_id가 없음
    # profile = _get_profile_dict(db, sess.profile_id)
    # ✅ OpicSession.user_id로 프로필 조회
    profile = _get_profile_dict(db, sess.user_id)

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