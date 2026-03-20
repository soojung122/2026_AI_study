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

from models import UserProfile, OpicSession
from models import OpicTurn as OpicTurnModel

from services.examiner import generate_next_question
from services.rater import rate_session


# 🔥 세션 상태 저장 (핵심)
SESSION_STATE = {}


# ----------------------------
# DB helpers
# ----------------------------
def create_profile(db: Session, profile: dict, user_id: int) -> int:
    existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    hobbies = profile.get("hobbies", {})

    if existing:
        existing.name = profile["name"]
        existing.job = profile["job"]
        existing.city = profile.get("city")
        existing.hobbies_json = json.dumps(hobbies, ensure_ascii=False)
        existing.speaking_style = profile.get("speaking_style")

        db.commit()
        return existing.user_id

    db_obj = UserProfile(
        user_id=user_id,
        name=profile["name"],
        job=profile["job"],
        city=profile.get("city"),
        hobbies_json=json.dumps(hobbies, ensure_ascii=False),
        speaking_style=profile.get("speaking_style"),
    )
    db.add(db_obj)
    db.commit()
    return db_obj.user_id


def create_session(db: Session, user_id: int, goal_grade: str, target_count: int = 12) -> int:
    db_obj = OpicSession(
        user_id=user_id,
        goal_grade=goal_grade,
        target_count=target_count,
        status="RUNNING",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj.session_id


def save_turn(db: Session, session_id: int, role: str, text: str) -> None:
    db.add(OpicTurnModel(session_id=session_id, role=role, text=text))
    db.commit()


def get_turns(db: Session, session_id: int) -> List[OpicTurnModel]:
    q = db.query(OpicTurnModel).filter(OpicTurnModel.session_id == session_id)

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
    prof = db.query(UserProfile).filter(UserProfile.user_id == profile_id).first()
    if not prof:
        raise ValueError("profile not found")

    try:
        hobbies = json.loads(prof.hobbies_json) if prof.hobbies_json else {}
    except Exception:
        hobbies = {}

    return {
        "name": prof.name,
        "job": prof.job,
        "city": prof.city,
        "hobbies": hobbies,
        "speaking_style": getattr(prof, "speaking_style", None),
    }


# ----------------------------
# Topic utilities
# ----------------------------
TOPIC_ROOT = os.getenv("OPIC_TOPIC_DIR", "topic")


def _grade_dir(goal_grade: str) -> str:
    g = (goal_grade or "").upper().strip()
    return "IM" if g == "IM" else "IH_AL"


@lru_cache(maxsize=64)
def _list_bank_topics(goal_grade: str, mode: str) -> list[str]:
    gdir = _grade_dir(goal_grade)
    m = (mode or "survey").lower().strip()
    folder = os.path.join(TOPIC_ROOT, gdir, m)

    if not os.path.isdir(folder):
        return []

    return [
        os.path.splitext(f)[0]
        for f in os.listdir(folder)
        if f.endswith(".txt")
    ]


def _tokenize(s: str) -> set[str]:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9_ ]+", " ", s)
    return set(s.split())


def normalize_topic_to_bank(goal_grade: str, mode: str, raw: str):
    raw = (raw or "").lower().strip()
    bank = _list_bank_topics(goal_grade, mode)

    if raw in bank:
        return raw, True

    raw_tokens = _tokenize(raw)

    best, score = None, 0
    for t in bank:
        t_tokens = _tokenize(t)
        s = len(raw_tokens & t_tokens)
        if raw in t or t in raw:
            s += 3
        if s > score:
            best, score = t, s

    return (best, True) if best else (raw, False)


# ----------------------------
# topic 추출 (순서 유지 핵심 🔥)
# ----------------------------
def extract_valid_topics(profile: dict, goal_grade: str, mode: str) -> list[str]:
    hobbies = profile.get("hobbies")
    raw = []

    if isinstance(hobbies, list):
        raw.extend(hobbies)

    elif isinstance(hobbies, dict):
        for v in hobbies.values():
            if isinstance(v, list):
                raw.extend(v)
            elif isinstance(v, str):
                raw.append(v)

    raw = [str(x).lower().strip() for x in raw if x]

    valid = []
    for r in raw:
        t, matched = normalize_topic_to_bank(goal_grade, mode, r)
        if matched:
            valid.append(t)

    # 🔥 순서 유지 + 중복 제거
    return list(dict.fromkeys(valid))


# ----------------------------
# 🔥 핵심: topic 흐름 제어
# ----------------------------
def get_next_topic_and_mode(session_id: int, topics: list[str], goal_grade: str):

    state = SESSION_STATE.get(session_id)

    # 최초 1회만 topics 고정
    if not state:
        if not topics:
            topics = ["home"]

        state = {
            "topics": topics,
            "topic_index": 0,
            "question_count": 0,
            "mode": "survey"
        }

    topics = state["topics"]

    # 3문제마다 topic 변경
    if state["question_count"] >= 3:
        state["topic_index"] = (state["topic_index"] + 1) % len(topics)
        state["question_count"] = 0

        # 🔥 돌발 확률
        if random.random() < 0.3:
            state["mode"] = "sudden"
        else:
            state["mode"] = "survey"

    state["question_count"] += 1

    # topic 선택
    if state["mode"] == "sudden":
        sudden_topics = _list_bank_topics(goal_grade, "sudden")
        topic = random.choice(sudden_topics) if sudden_topics else "home"
    else:
        topic = topics[state["topic_index"]]

    SESSION_STATE[session_id] = state

    return topic, state["mode"]


# ----------------------------
# session summary
# ----------------------------
def get_session_summary(db: Session, session_id: int) -> Dict[str, Any]:
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()

    return {
        "sessionId": session_id,
        "status": sess.status,
        "answered": _count_user_answers(db, session_id),
        "targetCount": sess.target_count,
        "goalGrade": sess.goal_grade,
        "profileId": sess.user_id,
    }


# ----------------------------
# Session UX
# ----------------------------
def seed_first_question(db: Session, session_id: int) -> Dict[str, Any]:
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    profile = _get_profile_dict(db, sess.user_id)

    topics = extract_valid_topics(profile, sess.goal_grade, "survey")

    topic_name, mode = get_next_topic_and_mode(
        session_id, topics, sess.goal_grade
    )

    q = generate_next_question(
        profile=profile,
        goal_grade=sess.goal_grade,
        history=[],
        last_user_answer=None,
        is_first=True,
        topic_name=topic_name,
        mode=mode,
    )

    save_turn(db, session_id, "EXAMINER", q)

    return {
        "sessionId": session_id,
        "questionText": q,
        "turnIndex": 0,
    }


def run_examiner_turn(db: Session, session_id: int, user_input: str) -> Dict[str, Any]:
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()
    profile = _get_profile_dict(db, sess.user_id)

    topics = extract_valid_topics(profile, sess.goal_grade, "survey")

    topic_name, mode = get_next_topic_and_mode(
        session_id, topics, sess.goal_grade
    )

    turns = get_turns(db, session_id)

    save_turn(db, session_id, "USER", user_input)

    history = (
        [{"role": t.role, "text": t.text} for t in turns[-12:]]
        + [{"role": "USER", "text": user_input}]
    )

    q = generate_next_question(
        profile=profile,
        goal_grade=sess.goal_grade,
        history=history,
        last_user_answer=user_input,
        is_first=False,
        topic_name=topic_name,
        mode=mode,
    )

    save_turn(db, session_id, "EXAMINER", q)

    return {
        "sessionId": session_id,
        "questionText": q,
        "turnIndex": _count_user_answers(db, session_id),
    }


# ----------------------------
# Rater
# ----------------------------
def end_and_rate_session(db: Session, session_id: int, force: bool = False) -> dict:
    sess = db.query(OpicSession).filter(OpicSession.session_id == session_id).first()

    turns = get_turns(db, session_id)
    profile = _get_profile_dict(db, sess.user_id)

    transcript = [{"role": t.role, "text": t.text} for t in turns]

    report = rate_session(
        profile=profile,
        goal_grade=sess.goal_grade,
        target_count=sess.target_count,
        transcript=transcript,
    )

    sess.status = "ENDED"
    sess.report_json = json.dumps(report, ensure_ascii=False)
    sess.ended_at = datetime.utcnow()

    db.commit()
    return report