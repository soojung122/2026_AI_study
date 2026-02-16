# services/rater.py
import json
from typing import Any, Dict, List

from services.llm_gemini import rater_evaluate_session_json as _rater_llm


def _safe_json_load(text: str) -> Dict[str, Any]:
    """
    Gemini가 ```json ... ``` 감싸거나 앞뒤 텍스트를 붙이는 경우 방어
    """
    if not text:
        raise ValueError("Empty JSON response")

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # 혹시 앞뒤에 텍스트가 붙으면, 첫 { 부터 마지막 } 까지 잘라서 파싱 시도
    if "{" in cleaned and "}" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def rate_session(
    *,
    profile: Dict[str, Any],
    goal_grade: str,
    target_count: int,
    transcript: List[Dict[str, str]],
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Role B: Rater
    - JSON only 결과를 강제
    - 파싱 실패 시 재시도 (서비스 로직에서 안정성 확보)
    """
    last_err: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            result = _rater_llm(
                profile=profile,
                goal_grade=goal_grade,
                target_count=target_count,
                transcript=transcript,
            )
            # llm_gemini가 dict를 이미 반환해도, 문자열로 올 가능성까지 방어
            if isinstance(result, dict):
                return result
            return _safe_json_load(str(result))
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Rater JSON parsing failed after retries: {last_err}")
