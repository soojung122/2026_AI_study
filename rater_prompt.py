# rater_prompt.py
from __future__ import annotations

import json
from typing import Any, Dict, List


def build_rater_system_prompt() -> str:
    # 규칙/역할/출력형식 강제는 system에 몰아넣는 게 안정적
    return """
You are an OPIC speaking test rater.

Hard rules:
- Output ONLY valid JSON. (No markdown, no code fences, no extra text)
- Do NOT add any explanation outside JSON.
- Use strict and realistic scoring.

Evaluate using these criteria:
- Task completion (relevance, answered what was asked)
- Coherence (structure, logical flow, transitions)
- Fluency (flow, pauses, repetitions)
- Grammar accuracy (error frequency and severity)
- Vocabulary range (variety, precision)
- Naturalness (spoken-like phrasing, confidence)

Return JSON that matches the required schema exactly.
""".strip()


def build_rater_user_prompt(
    *,
    profile: Dict[str, Any],
    goal_grade: str,
    target_count: int,
    transcript: List[Dict[str, str]],
) -> str:
    # 모델에게 "입력 데이터"와 "반드시 지켜야 하는 JSON 스키마"를 user에 제공
    payload = {
        "target_grade": goal_grade,
        "number_of_questions": target_count,
        "profile": profile,
        "transcript": transcript,
        "required_json_schema": {
            "estimated_grade": "string (one of: IM1, IM2, IM3, IH, AL)",
            "overall_score": "number (0-100)",
            "strengths": ["string"],
            "weaknesses": ["string"],
            "grammar_issues": ["string"],
            "vocabulary_issues": ["string"],
            "improvement_suggestions": ["string"],
            "model_answer_examples": ["string"],
        },
        "grading_notes": [
            "estimated_grade must be one of IM1/IM2/IM3/IH/AL",
            "overall_score is 0-100 and should align with estimated_grade",
            "model_answer_examples should be improved sample answers in natural spoken English",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)