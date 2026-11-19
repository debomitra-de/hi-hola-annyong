from planner.models import LessonPlan
from planner.templates import template_lesson_plan
from planner.validator import validate_lesson_plan


class LessonPlanner:
    def plan(
        self,
        source_text: str,
        level: str,
        due_items: list,
    ) -> LessonPlan:
        if level not in {"A1", "A2", "B1"}:
            raise ValueError("level must be A1, A2, or B1")
        if len(due_items) > 20:
            raise ValueError("planner receives at most 20 due items")

        topic = source_text.strip() or "conversation"
        payload = template_lesson_plan(level, topic, due_items)

        try:
            return validate_lesson_plan(payload)
        except ValueError:
            fallback = template_lesson_plan(level, "conversation", [])
            return validate_lesson_plan(fallback)
