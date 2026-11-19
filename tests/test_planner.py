import pytest

from planner.plan import LessonPlanner
from planner.validator import validate_lesson_plan


def test_topic_lesson_has_conversation_goals():
    plan = LessonPlanner().plan("restaurant", "A1", [])

    assert plan.source.type == "topic"
    assert plan.source.ref == "restaurant"
    assert plan.conversation_goals
    assert "restaurant" in plan.conversation_goals[0].objective.lower()


@pytest.mark.parametrize("count", [0, 3, 20])
def test_due_item_limits_accept_valid_counts(count):
    due_items = [{"lemma": f"word_{index}"} for index in range(count)]

    plan = LessonPlanner().plan("restaurant", "A2", due_items)

    assert len(plan.weak_items) <= 20


def test_planner_rejects_more_than_twenty_due_items():
    due_items = [{"lemma": f"word_{index}"} for index in range(21)]

    with pytest.raises(ValueError, match="at most 20"):
        LessonPlanner().plan("restaurant", "A1", due_items)


def test_plan_validator_rejects_more_than_three_new_words():
    plan_payload = {
        "level": "A1",
        "source": {"type": "topic", "ref": "restaurant"},
        "new_words": ["uno", "dos", "tres", "cuatro"],
        "conversation_goals": [
            {
                "objective": "Practise restaurant conversation",
                "target_phrases": ["la cuenta"],
            }
        ],
    }

    with pytest.raises(ValueError, match="at most 3"):
        validate_lesson_plan(plan_payload)
