from typing import Literal

from planner.models import LessonPlan


class LessonEngine:
    def __init__(self, plan: LessonPlan) -> None:
        self.plan = plan
        self.step = 0
        self.turns: list[dict] = []
        self.ended = False

    @property
    def mode(self) -> Literal["lesson", "quiz", "summary"]:
        if self.ended:
            return "summary"
        return "lesson"

    def record_turn(self, learner_text: str, tutor_message: dict) -> dict:
        if not isinstance(learner_text, str):
            raise TypeError("learner_text must be a string")
        if not learner_text.strip():
            raise ValueError("learner_text cannot be empty")
        if self.mode != "lesson":
            raise RuntimeError("lesson is complete")

        turn = {
            "step": self.step + 1,
            "learner_text": learner_text,
            "tutor_message": dict(tutor_message),
        }
        self.turns.append(turn)
        self.step += 1
        return turn

    def end_lesson(self) -> None:
        self.ended = True

    def checkpoint(self) -> dict:
        return {
            "step": self.step,
            "turns": [dict(turn) for turn in self.turns],
            "plan": self.plan.model_dump(),
            "ended": self.ended,
        }


class PlacementEngine:
    QUESTIONS = [
        ("¿Cómo te llamas?", ["me llamo ana", "soy ana"]),
        ("¿De dónde eres?", ["soy de madrid", "soy española"]),
        ("¿Dónde compraste el libro?", ["lo compre en la tienda"]),
        ("Explica por qué estudias español.", ["estudio español porque"]),
        ("¿Qué harás si tienes tiempo libre?", ["estudiaré", "viajaré"]),
    ]

    def __init__(self) -> None:
        self.step = 0
        self.correct_count = 0

    @property
    def complete(self) -> bool:
        return self.step >= len(self.QUESTIONS)

    @property
    def current_question(self) -> str | None:
        if self.complete:
            return None
        return self.QUESTIONS[self.step][0]

    def submit_answer(self, answer: str) -> bool:
        if self.complete:
            raise RuntimeError("placement is complete")
        if not isinstance(answer, str):
            raise TypeError("answer must be a string")

        _, expected = self.QUESTIONS[self.step]
        normalised = " ".join(answer.strip().casefold().split())
        correct = any(
            normalised == item or normalised.startswith(item)
            for item in expected
        )
        if correct:
            self.correct_count += 1
        self.step += 1
        return correct

    @property
    def level(self) -> str | None:
        if not self.complete:
            return None
        if self.correct_count >= 4:
            return "B1"
        if self.correct_count >= 2:
            return "A2"
        return "A1"
