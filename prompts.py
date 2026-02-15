def build_opic_prompt(profile: dict, goal_grade: str, question: str, constraints: dict) -> str:
    grade_rules = {
        "IM": {
            "length": "90~130 words",
            "complexity": "simple sentences, a few connectors",
            "mistakes": "0~1 minor mistake allowed (natural)"
        },
        "IH": {
            "length": "140~190 words",
            "complexity": "varied sentence patterns, clear transitions",
            "mistakes": "0~1 minor mistake allowed"
        },
        "AL": {
            "length": "190~240 words",
            "complexity": "storytelling, idiomatic but not forced, nuance",
            "mistakes": "0 mistakes preferred"
        }
    }

    r = grade_rules.get(goal_grade, grade_rules["IH"])

    return f"""
You are an OPIc English speaking coach and answer generator.

[User Profile]
- Name: {profile.get("name")}
- Job/Role: {profile.get("job")}
- City: {profile.get("city")}
- Hobbies: {", ".join(profile.get("hobbies", []))}
- Speaking style: {profile.get("speaking_style")}

[Goal Grade]
- {goal_grade}

[OPIc Question]
- {question}

[Output Requirements]
- Output ONLY the final answer script in English.
- Target length: {r["length"]}
- Difficulty: {r["complexity"]}
- Naturalness: {r["mistakes"]}
- Must include: 1 short opener + 1 personal detail + 1 example/mini-story + 1 wrap-up.
- Avoid: overly formal writing, lists, headings, meta explanations.

[Constraints]
{constraints_to_text(constraints)}
""".strip()


def constraints_to_text(constraints: dict) -> str:
    lines = []
    for k, v in constraints.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)
