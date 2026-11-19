from typing import Any


def template_lesson_plan(
    level: str,
    topic: str,
    due_items: list,
) -> dict[str, Any]:
    normalized_topic = topic.strip().lower()
    weak_items = [
        item.get("lemma")
        if isinstance(item, dict)
        else str(item)
        for item in due_items[:20]
    ]
    weak_items = [item for item in weak_items if item]

    if normalized_topic == "restaurant":
        goals = [
            {
                "objective": "Practise a natural restaurant conversation",
                "target_phrases": ["una mesa", "la cuenta", "pedir"],
            }
        ]
    else:
        goals = [
            {
                "objective": f"Practise an open-ended conversation about {topic}",
                "target_phrases": [],
            }
        ]

    return {
        "level": level,
        "source": {"type": "topic", "ref": topic},
        "new_words": ["la cuenta", "pedir", "la mesa"][:3],
        "conversation_goals": goals,
        "weak_items": weak_items,
    }
