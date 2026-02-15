
import os
from dotenv import load_dotenv
from google import genai

from prompts import build_opic_prompt
from policy import OUTPUT_CONSTRAINTS

load_dotenv()

def generate_opic_answer(profile: dict, goal_grade: str, question: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 .env에 없습니다.")

    client = genai.Client(api_key=api_key)

    prompt = build_opic_prompt(
        profile=profile,
        goal_grade=goal_grade,
        question=question,
        constraints=OUTPUT_CONSTRAINTS
    )

   
    resp = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )

    return resp.text.strip()

if __name__ == "__main__":
    profile = {
        "name": "jung",
        "job": "college student",
        "city": "Yongin",
        "hobbies": ["photo shooting", "cooking"],
        "speaking_style": "natural"  # natural / confident / calm 등
    }
    goal_grade = "IH"  # IM / IH / AL
    question = "Tell me about your home and what you like about it."

    print(generate_opic_answer(profile, goal_grade, question))
