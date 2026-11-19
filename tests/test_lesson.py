from planner.plan import LessonPlanner
from tutor.lesson import LessonEngine, PlacementEngine


def test_lesson_records_natural_conversation_turns():
    plan = LessonPlanner().plan("restaurant", "A1", [])
    lesson = LessonEngine(plan)

    turn = lesson.record_turn(
        "Quiero una mesa.",
        {"kind": "feedback", "es": "Muy bien.", "en": "Very good.", "items": []},
    )

    assert turn["step"] == 1
    assert lesson.step == 1


def test_lesson_checkpoint_round_trips_state():
    plan = LessonPlanner().plan("restaurant", "A1", [])
    lesson = LessonEngine(plan)
    lesson.record_turn(
        "Me llamo Ana.",
        {"kind": "prompt", "es": "¿De dónde eres?", "en": "Where are you from?", "items": []},
    )

    checkpoint = lesson.checkpoint()

    assert checkpoint["step"] == 1
    assert checkpoint["turns"][0]["learner_text"] == "Me llamo Ana."
    assert checkpoint["plan"]["source"]["ref"] == "restaurant"


def test_placement_maps_answers_to_cefr_levels():
    placement = PlacementEngine()
    answers = [
        "Me llamo Ana",
        "Soy de Madrid",
        "Lo compré en la tienda",
        "Estudio español porque quiero viajar",
        "Viajaré",
    ]

    for answer in answers:
        placement.submit_answer(answer)

    assert placement.complete
    assert placement.level == "B1"


def test_placement_stays_after_questions():
    placement = PlacementEngine()

    for _ in placement.QUESTIONS:
        placement.submit_answer("no entiendo")

    assert placement.level == "A1"
