# models.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, UniqueConstraint, Index
from sqlalchemy.sql import func
from db import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    # ✅ AI PK로 변경
    profile_id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(50), nullable=False)

    # ✅ (name, job) UK를 제대로 쓰려면 job을 NOT NULL 권장
    #    (MySQL은 NULL이 여러 개 허용되어 UK가 의도와 다를 수 있음)
    job = Column(String(100), nullable=False)

    city = Column(String(100), nullable=True)
    hobbies_json = Column(Text, nullable=True)
    speaking_style = Column(String(30), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "job", name="uk_user_profiles_name_job"),
    )


class OpicSession(Base):
    __tablename__ = "opic_sessions"

    # ✅ AI PK로 변경
    session_id = Column(Integer, primary_key=True, autoincrement=True)

    # ✅ FK 타입도 Integer로 맞춤
    profile_id = Column(Integer, ForeignKey("user_profiles.profile_id"), nullable=False)

    goal_grade = Column(String(10), nullable=False)

    target_count = Column(Integer, nullable=False, server_default="12")
    status = Column(String(20), nullable=False, server_default="RUNNING")
    ended_at = Column(DateTime, nullable=True)

    # MySQL에서 LONGTEXT 쓰려면 DDL에서 변경 권장 (SQLAlchemy Text는 보통 TEXT)
    report_json = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_opic_sessions_profile_id", "profile_id"),
        Index("idx_opic_sessions_status", "status"),
    )


class OpicTurn(Base):
    __tablename__ = "opic_turns"

    # ✅ PK 이름을 id로 통일 (flow에서 OpicTurnModel.id를 쓰는 구조와 맞추기)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ✅ FK 타입 Integer로 맞춤
    session_id = Column(Integer, ForeignKey("opic_sessions.session_id"), nullable=False)

    # ✅ role 값 통일: EXAMINER / USER
    role = Column(String(20), nullable=False)

    text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_opic_turns_session_created_at", "session_id", "created_at"),
        Index("idx_opic_turns_session_role", "session_id", "role"),
    )
