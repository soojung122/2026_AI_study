# services/examiner.py
import re
from typing import Any, Dict, List, Optional

# from services.llm_gemini import examiner_generate_question as _examiner_llm
from question_prompt import examiner_generate_question as _examiner_llm

def _enforce_single_question(text: str) -> str:
    """
    - 질문 1개만 남긴다
    - 번호목록/여러 줄이면 첫 질문만
    """
    if not text:
        return "Could you tell me more about that?"

    s = text.strip()

    # 코드펜스/따옴표 같은 흔한 노이즈 제거
    s = s.replace("```", "").strip().strip('"').strip("'")

    # 여러 줄이면 첫 줄 우선
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    s = lines[0] if lines else s

    # 번호 목록 시작 제거 (e.g., "1. ...")
    s = re.sub(r"^\s*\d+\.\s*", "", s).strip()

    # 물음표 기준으로 첫 질문만
    if "?" in s:
        s = s.split("?", 1)[0].strip() + "?"
    else:
        # 물음표가 없으면 질문형으로 보정
        s = s.rstrip(".") + "?"

    # 너무 짧거나 이상하면 fallback
    if len(s) < 8:
        return "Could you tell me more about that?"

    return s


def generate_next_question(
    *,
    profile: Dict[str, Any],
    goal_grade: str,
    history: List[Dict[str, str]],
    last_user_answer: Optional[str],
    topic_name: str = "home",     # ✅ 추가
    mode: str = "survey",         # ✅ 추가
    is_first: bool = False,
) -> str:
    """
    Role A: Examiner
    - 질문 생성만 담당
    - '질문 1개' 규칙을 여기서 강제
    """
    raw = _examiner_llm(
        profile=profile,
        goal_grade=goal_grade,
        history=history,
        last_user_answer=last_user_answer,
        topic_name=topic_name,  # ✅ 추가
        mode=mode,              # ✅ 추가
        is_first=is_first,
    )
    return _enforce_single_question(raw)
