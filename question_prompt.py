import os
import json
from google import genai

from functools import lru_cache

def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 .env에 없습니다.")
    return genai.Client(api_key=api_key)


MODEL_NAME = "models/gemini-2.5-flash"

TOPIC_ROOT = os.getenv("OPIC_TOPIC_DIR", "topic")
VALID_MODES = {"survey", "sudden", "advance"}


def _grade_dir(goal_grade: str) -> str:
    g = (goal_grade or "").upper().strip()
    return "IM" if g == "IM" else "IH_AL"


def _resolve_mode(goal_grade: str, mode: str) -> str:
    m = (mode or "survey").lower().strip()

    if m not in VALID_MODES:
        return "survey"

    if _grade_dir(goal_grade) == "IM" and m == "advance":
        return "survey"

    return m


@lru_cache(maxsize=512)
def _load_question_bank(goal_grade: str, mode: str, topic_name: str) -> list[str]:
    gdir = _grade_dir(goal_grade)

    path = os.path.join(
        TOPIC_ROOT,
        gdir,
        mode,
        f"{topic_name.lower()}.txt",
    )

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]


def _level_rules(goal_grade: str) -> str:
    g = (goal_grade or "").upper().strip()

    if g == "IM":
        return """
[LEVEL RULES: IM]
- Use easy words and short-to-medium sentences.
- Ask ONE clear question.
""".strip()

    if g == "IH":
        return """
[LEVEL RULES: IH]
- Use natural spoken English.
- Ask ONE question with some detail.
""".strip()

    if g == "AL":
        return """
[LEVEL RULES: AL]
- Use advanced natural English.
- Ask ONE concise but deep question.
""".strip()

    return """
[LEVEL RULES: DEFAULT]
- Ask ONE natural question.
""".strip()


def _clean_to_one_question(text: str) -> str:
    t = (text or "").strip()
    t = t.replace("```", "").strip().strip('"').strip("'").strip()

    if "?" in t:
        t = t.split("?", 1)[0].strip() + "?"
        return t

    for sep in ["\n", ".", "!", ";"]:
        if sep in t:
            t = t.split(sep, 1)[0].strip()
            break

    if not t.endswith("?"):
        t = t.rstrip(".!;") + "?"
    return t


def examiner_generate_question(
    profile: dict,
    goal_grade: str,
    history: list,
    last_user_answer: str | None,
    topic_name: str,
    mode: str,
    is_first: bool = False,
) -> str:

    # 🔥 1️⃣ 첫 질문 무조건 자기소개
    if is_first:
        return "Could you tell me a little about yourself?"

    # 🔥 2️⃣ 답변 없으면 다음 질문 생성 금지
    if not last_user_answer:
        return None

    client = _client()

    level_block = _level_rules(goal_grade)
    history_short = history[-6:] if isinstance(history, list) else history

    resolved_mode = _resolve_mode(goal_grade, mode)
    bank = _load_question_bank(goal_grade, resolved_mode, topic_name)

    if bank:
        bank_block = "\n".join(f"- {q}" for q in bank[:40])
    else:
        bank_block = "(No question bank available. Create a natural OPIc question for this topic.)"

    follow_block = """
[FOLLOW-UP MODE]
- Base the question on the last user answer.
- Ask ONE more detail, example, reason, feeling, or a small hypothetical.
""".strip()

    prompt = f"""
당신은 실제 OPIc 영어 말하기 시험의 시험관입니다.

[ABSOLUTE OUTPUT RULES]
- 출력은 반드시 영어로만.
- 질문은 반드시 1개만.
- 평가/피드백/점수/조언 금지.
- 질문 외 문장 금지.

Target grade: {goal_grade}
Mode: {resolved_mode}
Topic: {topic_name}

{level_block}

{follow_block}

[QUESTION BANK RULE]
- Your question MUST be based on the bank.
- Pick ONE question from the bank OR rewrite ONE.

Question bank:
{bank_block}

Profile:
{profile}

Conversation history:
{history_short}

Last user answer:
{last_user_answer}
""".strip()

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={"temperature": 0.55},
    )

    text = (resp.text or "").strip()
    return _clean_to_one_question(text)


def rater_evaluate_session_json(
    profile: dict,
    goal_grade: str,
    target_count: int,
    transcript: list,
) -> dict:

    client = _client()

    prompt = f"""
You are an OPIc rater.

Return ONLY JSON.

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

Transcript:
{transcript}
""".strip()

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = resp.text.strip()

    try:
        return json.loads(text)
    except Exception:
        cleaned = text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)