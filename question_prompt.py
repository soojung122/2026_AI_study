# services/llm_gemini.py

import os
import json
from google import genai


def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 .env에 없습니다.")
    return genai.Client(api_key=api_key)


MODEL_NAME = "models/gemini-2.5-flash"


# =========================
# Level Prompting (IM/IH/AL)
# =========================
def _level_rules(goal_grade: str) -> str:
    g = (goal_grade or "").upper().strip()

    # IM(대략 3-4) / IH(대략 5) / AL(대략 6) 느낌으로 프롬프트를 강하게 고정
    if g == "IM":
        return """
[LEVEL RULES: IM]
- Use easy words and short-to-medium sentences.
- Mostly present tense + simple past only if needed.
- Ask ONE clear question. Avoid multi-part questions.
- Keep it natural and friendly (not textbook).
- Avoid abstract topics and trade-offs.
- No probing like "pros and cons" unless very simple.
""".strip()

    if g == "IH":
        return """
[LEVEL RULES: IH]
- Use natural spoken English with varied sentence patterns.
- Encourage a specific example (simple past) or details (when/where/who).
- Ask ONE question that is still single-focus (no long multi-part).
- It can be a probing question, but keep it concise.
- You may ask "why" OR "how" (not both in the same question).
""".strip()

    if g == "AL":
        return """
[LEVEL RULES: AL]
- Use advanced but natural spoken English (no forced idioms).
- Encourage depth: feelings, reasoning, reflection, or problem-handling.
- Ask ONE concise probing question (single sentence is preferred).
- You MAY include a light hypothetical ("What would you do if...") OR comparison,
  but do not chain multiple sub-questions.
- The question should invite storytelling and nuanced explanation.
""".strip()

    # fallback
    return """
[LEVEL RULES: DEFAULT]
- Ask ONE natural follow-up question in spoken English.
""".strip()


def _clean_to_one_question(text: str) -> str:
    """모델이 실수로 여러 문장/여러 질문을 뱉을 때 1개 질문으로 강제 정리"""
    t = (text or "").strip()

    # 코드블록/따옴표 제거
    t = t.replace("```", "").strip().strip('"').strip("'").strip()

    # 가장 첫 '?'까지 자르기 (없으면 문장 1개만)
    if "?" in t:
        t = t.split("?", 1)[0].strip() + "?"
        return t

    # 물음표가 없으면 문장 분리해서 1문장만
    for sep in ["\n", ".", "!", ";"]:
        if sep in t:
            t = t.split(sep, 1)[0].strip()
            break

    # 끝이 질문처럼 보이게 만들기(최후의 안전장치)
    if not t.endswith("?"):
        t = t.rstrip(".!;") + "?"
    return t


# ==========================================================
# Role A: Examiner (질문 1개만 생성) ✅ 레벨별 프롬프팅 강화 버전
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
    - ✅ 목표 등급(IM/IH/AL)별 난이도/스타일 규칙 반영
    """

    client = _client()

    level_block = _level_rules(goal_grade)

    # history가 너무 길면 모델이 산만해져서, "최근 N턴만" 쓰는 것도 좋아요.
    # (지금은 안전하게 마지막 6개만 사용)
    history_short = history[-6:] if isinstance(history, list) else history

    # 첫 질문이면 토픽 자연스럽게 시작, 아니면 직전 답변을 기반으로 follow-up
    first_block = """
[FIRST QUESTION MODE]
- Start a natural topic based on the profile (hobbies, city, daily routine).
- Do NOT say "Let's begin" or explain the rules.
""".strip()

    follow_block = """
[FOLLOW-UP MODE]
- Base the question on the last user answer.
- Ask for ONE more detail, example, reason, feeling, or a small hypothetical.
""".strip()

    mode_block = first_block if is_first else follow_block

    # 한국어 지시 + 영어 출력 규칙(지우님 기존 스타일 참고)
    prompt = f"""
당신은 실제 OPIc 영어 말하기 시험의 시험관입니다.

[ABSOLUTE OUTPUT RULES]
- 출력은 반드시 영어로만.
- 질문은 반드시 1개만.
- 평가/피드백/점수/조언/해설/서문 금지.
- 질문 외의 어떤 문장도 쓰지 마세요. (예: "Sure!", "Here is..." 금지)
- 가능한 한 한 문장으로.

Target grade: {goal_grade}

{level_block}

{mode_block}

Profile (JSON-like):
{profile}

Conversation history (recent):
{history_short}

Last user answer:
{last_user_answer}
""".strip()

    resp = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        # 너무 창의적으로 튀면 규칙 위반할 수 있어서 등급별로 약간만 조절
        config={
            "temperature": 0.35 if (goal_grade or "").upper().strip() == "IM" else 0.55 if (goal_grade or "").upper().strip() == "IH" else 0.65
        },
    )

    text = (resp.text or "").strip()
    return _clean_to_one_question(text)


# ==========================================================
# Role B: Rater (JSON only)  (기존 그대로)
# ==========================================================
def rater_evaluate_session_json(
    profile: dict,
    goal_grade: str,
    target_count: int,
    transcript: list,
) -> dict:
    """
    - 세션 전체를 루브릭 기반으로 평가
    - 반드시 JSON으로만 출력
    """

    client = _client()

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

    try:
        return json.loads(text)
    except Exception:
        cleaned = text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)