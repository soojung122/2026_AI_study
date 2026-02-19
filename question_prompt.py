# -*- coding: utf-8 -*-
"""
OPIc 질문 생성(Gemini) → Google Cloud TTS로 메인 질문만 '저장 없이' 재생 (캐시로 비용 절약)
컨트롤:
- Enter: 다음 질문
- r: 현재 질문 다시 듣기(replay)  ✅ 캐시 재생(추가 과금 거의 X)
- p: 이전 질문 듣기(prev)
- q: 종료
"""

from dotenv import load_dotenv
import os
import json
import io
import pygame
from google import genai
from google.cloud import texttospeech

# =========================
# Env
# =========================
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY가 없습니다. .env에 GEMINI_API_KEY=... 를 넣어주세요.")

gemini_client = genai.Client(api_key=API_KEY)

# =========================
# TTS Init (no file saving)
# =========================
pygame.mixer.init()
tts_client = texttospeech.TextToSpeechClient()

# ✅ 메모리 캐시: (voice_name, rate, pitch, text) → mp3_bytes
TTS_CACHE = {}

# ✅ 캐시 메모리 폭주 방지(너무 많이 쌓이면 오래된 것부터 삭제)
MAX_CACHE_ITEMS = 200


def _cache_key(text: str, voice_name: str, speaking_rate: float, pitch: float):
    # float은 키 안정성 위해 적당히 반올림
    return (voice_name, round(speaking_rate, 3), round(pitch, 3), text.strip())


def speak_text_google_cached(
    text: str,
    voice_name: str = "en-US-Neural2-F",  # 오픽 여성 느낌
    speaking_rate: float = 0.92,
    pitch: float = 2.0,
):
    """
    Google Cloud TTS → MP3 bytes → 메모리 재생 (파일 저장 X)
    ✅ 같은 문장은 캐시로 재생하여 API 재호출(=과금) 줄임
    """
    text = (text or "").strip()
    if not text:
        return

    key = _cache_key(text, voice_name, speaking_rate, pitch)

    # 1) 캐시에 있으면 API 호출 없이 재생
    if key in TTS_CACHE:
        mp3_bytes = TTS_CACHE[key]
    else:
        # 2) 없으면 TTS 호출 후 캐시에 저장
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )

        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        mp3_bytes = response.audio_content

        # 캐시 저장 (간단 LRU 흉내: 꽉 차면 임의로 하나 제거)
        if len(TTS_CACHE) >= MAX_CACHE_ITEMS:
            # dict는 insertion order 유지 → 가장 오래된 것 1개 제거
            oldest_key = next(iter(TTS_CACHE.keys()))
            del TTS_CACHE[oldest_key]
        TTS_CACHE[key] = mp3_bytes

    # 3) 재생 (BytesIO로 감싸기)
    audio_stream = io.BytesIO(mp3_bytes)
    pygame.mixer.music.load(audio_stream, "mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue


# =========================
# Prompt Builder (OPIc 스타일 강화, 한국어 지시 + 영어 출력)
# =========================
def build_question_prompt(level_bucket: str, topic: str, num_questions: int = 3) -> str:
    level_block = f"""
[레벨 규칙]
- 레벨: {level_bucket}

레벨 1-2:
- 매우 쉬운 단어/짧은 문장
- 현재 시제 중심
- follow-up 0~1개

레벨 3-4:
- 과거 경험 포함 (simple past)
- 이유/설명 1회 포함
- follow-up 1~2개

레벨 5-6 (IH~AL):
- 과거 경험 + 문제 상황 또는 가정(what if) 포함
- 감정/이유/해결 방법/비교(트레이드오프) 유도
- follow-up 2~3개 (최소 1개는 probing question)
""".strip()

    return f"""
당신은 실제 OPIc 영어 말하기 시험의 시험관입니다.

[시험 상황]
- 응시자 레벨: {level_bucket}
- 주제: {topic}
- 문항 수: 정확히 {num_questions}개

[오픽 질문 스타일 규칙 — 매우 중요]
1) 실제 시험관 말투처럼 자연스럽게 묻는다. (교과서 문장 금지)
2) 각 main 질문은 아래 유형 중 하나의 형태를 따른다:
   - 루틴/습관: "What do you usually...?" "How often...?"
   - 경험: "Tell me about a time when..." "Have you ever...?"
   - 문제/상황 대처: "What would you do if...?" "How would you handle...?"
   - 비교/선호/의견: "Which do you prefer... and why?" "What are the pros and cons...?"
3) follow-up은 main과 논리적으로 이어지고, 점점 더 구체적으로 파고든다.
   (when/where/who/details/feelings/reasons/results/solutions)
4) 질문은 길게 설명하지 말고, 시험처럼 간결하지만 자연스럽게.
5) 출력은 반드시 '영어'로 작성한다.

{level_block}

[출력 규칙]
- JSON만 출력 (설명/해설/서문 금지)
- 아래 스키마 그대로 (키 이름 고정)
- questions 배열 길이는 반드시 {num_questions}

출력(JSON):
{{
  "level": "{level_bucket}",
  "topic": "{topic}",
  "questions": [
    {{
      "main": "string",
      "followups": ["string"]
    }}
  ]
}}
""".strip()


def temperature_by_level(level_bucket: str) -> float:
    return {"1-2": 0.3, "3-4": 0.5, "5-6": 0.8}.get(level_bucket, 0.5)


# =========================
# Gemini Call
# =========================
def generate_questions(level: str, topic: str, num_questions: int = 3):
    prompt = build_question_prompt(level, topic, num_questions=num_questions)

    resp = gemini_client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": temperature_by_level(level),
        },
    )

    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("빈 응답이 왔습니다. API 키/쿼터/네트워크를 확인해주세요.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return {"raw_text": text}
        return {"raw_text": text}


# =========================
# Pretty Print
# =========================
def print_questions(result: dict):
    print("\n===== 생성 결과 =====")
    if "raw_text" in result:
        print(result["raw_text"])
        return

    print(f"Level: {result.get('level')}")
    print(f"Topic: {result.get('topic')}\n")

    questions = result.get("questions", [])
    for idx in range(len(questions)):
        q = questions[idx]
        main = (q.get("main") or "").strip()
        followups = q.get("followups", []) or []

        print(f"{idx+1}. {main}")
        for j in range(len(followups)):
            print(f"   - Follow-up {j+1}: {followups[j]}")
        print()


# =========================
# Interactive TTS (main only) with replay/prev + ✅cache
# =========================
def speak_interactive_main_only(
    result: dict,
    voice_name: str = "en-US-Neural2-F",
    speaking_rate: float = 0.92,
    pitch: float = 2.0,
):
    if "raw_text" in result:
        return

    questions = result.get("questions", []) or []
    if len(questions) == 0:
        print("질문이 없습니다.")
        return

    idx = 0  # 0-based

    def play_current():
        main = (questions[idx].get("main") or "").strip()
        if not main:
            print("현재 질문이 비어있습니다.")
            return
        print(f"\n🔊 Q{idx+1}: {main}")
        # ✅ 캐시 재생(Replay 시 과금 줄어듦)
        speak_text_google_cached(
            main,
            voice_name=voice_name,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )

    print("\n🎧 컨트롤: [Enter]=다음  r=다시듣기  p=이전  q=종료")
    print("   (비용 절약을 위해 메인 질문만 읽습니다. r은 캐시 재생)\n")

    # 첫 질문 바로 재생
    play_current()

    while True:
        cmd = input("\n명령 입력: ").strip().lower()

        if cmd == "q":
            print("종료합니다.")
            break
        elif cmd == "r":
            play_current()
        elif cmd == "p":
            if idx == 0:
                print("이미 첫 질문입니다.")
            else:
                idx -= 1
                play_current()
        else:
            # Enter 포함: 다음
            if idx >= len(questions) - 1:
                print("마지막 질문입니다. (r=다시듣기, p=이전, q=종료)")
            else:
                idx += 1
                play_current()


# =========================
# CLI
# =========================
def choose_level() -> str:
    print("\n레벨을 선택하세요:")
    print("1) 1-2 (초급)")
    print("2) 3-4 (중급)")
    print("3) 5-6 (IH~AL)")
    choice = input("입력(1/2/3 또는 직접 1-2/3-4/5-6): ").strip()

    mapping = {"1": "1-2", "2": "3-4", "3": "5-6"}
    if choice in mapping:
        return mapping[choice]
    if choice in ("1-2", "3-4", "5-6"):
        return choice

    print("⚠️ 입력이 애매해서 기본값(3-4)으로 진행합니다.")
    return "3-4"


def main():
    level = choose_level()
    topic = input("\n주제를 입력하세요 (예: travel, hobby, work, campus life, movie): ").strip() or "travel"

    n_raw = input("\n문항 수를 입력하세요 (기본 3): ").strip()
    try:
        num_questions = int(n_raw) if n_raw else 3
        if num_questions <= 0:
            num_questions = 3
    except ValueError:
        num_questions = 3

    result = generate_questions(level, topic, num_questions=num_questions)
    print_questions(result)

    use_tts = input("메인 질문을 음성으로 들을까요? (y/n): ").strip().lower()
    if use_tts == "y":
        speak_interactive_main_only(
            result,
            voice_name="en-US-Neural2-F",
            speaking_rate=0.92,
            pitch=2.0,
        )

    show_json = input("JSON 원문도 출력할까요? (y/n): ").strip().lower()
    if show_json == "y":
        print("\n===== JSON =====")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
