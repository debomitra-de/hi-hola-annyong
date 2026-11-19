from planner.models import LessonPlan

ENGLISH_WORDS = {
    "hello",
    "good",
    "morning",
    "evening",
    "please",
    "thank",
    "what",
    "where",
    "when",
    "how",
    "who",
    "want",
    "need",
    "table",
    "bill",
}


def validate_lesson_plan(payload: dict) -> LessonPlan:
    plan = LessonPlan.model_validate(payload)
    return plan
