from dotenv import load_dotenv
import os
from google.cloud import texttospeech

load_dotenv()

client = texttospeech.TextToSpeechClient()

def synthesize_speech(
    text: str,
    out_path: str = "tts_output.mp3",
    language_code: str = "en-US",
    voice_name: str = "en-US-Standard-C",
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
        pitch=pitch,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    with open(out_path, "wb") as out:
        out.write(response.audio_content)

    return out_path


if __name__ == "__main__":
    print("TTS 생성 시작...")
    path = synthesize_speech("Hello! This is a test for Google Text to Speech.", "tts_output.mp3")
    print("저장 완료:", path)
