# services/llm_gemini.py

import os
import json
from typing import Optional
from google import genai


def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 .env에 없습니다.")
    return genai.Client(api_key=api_key)


MODEL_NAME = "models/gemini-2.5-flash"


# ==========================================================
# Role A: Examiner (질문 1개만 생성)
# ==========================================================
def examiner_generate_question(
    profile: dict,
    goal_grade: str,
    history: list,
    last_user_answer: str | None,
    is_first: bool = False,
) -> str:
    """
    - 오픽 톤
    - 구어체
    - 반드시 질문 1개만 출력
    - 평가/피드백 절대 포함 금지
    """

    client = _client()

    prompt = f"""
You are an OPIc examiner.

Rules:
- Generate ONLY ONE natural follow-up question.
- Use conversational spoken English tone.
- Do NOT provide feedback.
- Do NOT evaluate.
- Do NOT explain.
- Output ONLY the question sentence.

Target grade: {goal_grade}

Profile:
{profile}

Conversation history:
{history}

Last user answer:
{last_user_answer}

If this is the first question, introduce a topic naturally.
""".strip()

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = resp.text.strip()

    # 🔒 안전장치: 질문 하나만 남기기
    if "?" in text:
        text = text.split("?")[0].strip() + "?"

    return text
    


# ==========================================================
# Role B: Rater (JSON only)
# ==========================================================
def rater_evaluate_session_json(
    profile: dict,
    goal_grade: str,
    target_count: int,
    transcript: list,
    *,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
) -> dict:
    """
    - 세션 전체를 루브릭 기반으로 평가
    - 반드시 JSON으로만 출력
    - system_prompt/user_prompt 주입 가능
    """

    client = _client()

    if system_prompt is not None and user_prompt is not None:
        prompt = f"""SYSTEM:
{system_prompt}

USER:
{user_prompt}
""".strip()
    else:
        # (기존 동작 유지용 fallback)
        prompt = f"""
You are an OPIc certified rater.

Evaluate the candidate based on the transcript.

Return ONLY valid JSON.
No explanation.
No markdown.
No extra text.

JSON schema:

{{
  "estimated_grade": "string",
  "overall_score": number,
  "strengths": ["string"],
  "weaknesses": ["string"],
  "grammar_issues": ["string"],
  "vocabulary_issues": ["string"],
  "improvement_suggestions": ["string"],
  "model_answer_examples": ["string"]
}}

Target grade: {goal_grade}
Number of questions: {target_count}

Profile:
{profile}

Transcript:
{transcript}
""".strip()

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = resp.text.strip()

    # 🔒 JSON 파싱 강제
    try:
        return json.loads(text)
    except Exception:
        cleaned = text.replace("```json", "").replace("```", "").strip()
        # 앞뒤 텍스트 방어: 첫 { ~ 마지막 } 잘라 파싱
        if "{" in cleaned and "}" in cleaned:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)
