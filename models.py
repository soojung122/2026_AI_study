# models.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, UniqueConstraint, Index, BigInteger, TIMESTAMP
from sqlalchemy.sql import func
from db import Base
# 260221 서은 relationship 추가 -> 파이썬 객체로 쓸 수 있게 하기위함
from sqlalchemy.orm import relationship

# 260221 서은 유저 추가
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    profile = relationship("UserProfile", back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    # ✅ 유저별 프로필 1개: user_id가 PK
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    user = relationship("User", back_populates="profile")  # 1:1

    name = Column(String(50), nullable=False)
    job = Column(String(100), nullable=False)

    city = Column(String(100), nullable=True)
    hobbies_json = Column(Text, nullable=True)
    speaking_style = Column(String(30), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ✅ 유저별 1개면 아래 UniqueConstraint는 제거 권장
    # __table_args__ = (
    #     UniqueConstraint("name", "job", name="uk_user_profiles_name_job"),
    # )


class OpicSession(Base):
    __tablename__ = "opic_sessions"

    # 260221 서은 유저 아이디와 연결
    # ✅ AI PK로 변경
    session_id = Column(Integer, primary_key=True, autoincrement=True)

    # ✅ FK 타입도 Integer로 맞춤
    user_id = Column(Integer, ForeignKey("user_profiles.user_id"), nullable=False)

    goal_grade = Column(String(10), nullable=False)

    target_count = Column(Integer, nullable=False, server_default="12")
    status = Column(String(20), nullable=False, server_default="RUNNING")
    ended_at = Column(DateTime, nullable=True)

    # MySQL에서 LONGTEXT 쓰려면 DDL에서 변경 권장 (SQLAlchemy Text는 보통 TEXT)
    report_json = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        # 260221 서은 -  인덱스 부분 이름 수정
        Index("idx_opic_sessions_user_id", "user_id"),
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
