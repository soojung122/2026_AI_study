from dotenv import load_dotenv
import os
from google.cloud import speech

# .env 로드
load_dotenv()

# Google STT 클라이언트 생성
client = speech.SpeechClient()


def transcribe_audio(audio_file_path):
    with open(audio_file_path, "rb") as f:
        content = f.read()

    audio = speech.RecognitionAudio(content=content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US",
        enable_automatic_punctuation=True,
        audio_channel_count=2,
    )

    response = client.recognize(config=config, audio=audio)

    if response.results:
        return response.results[0].alternatives[0].transcript

    return ""


# =========================
# 실행 테스트 코드
# =========================
if __name__ == "__main__":
    audio_path = "sample.wav"  # 같은 폴더에 있어야 함

    print("음성 인식 시작...")

    result = transcribe_audio(audio_path)

    print("STT 결과:", result)
