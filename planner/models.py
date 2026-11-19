from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["topic", "chapter"]
    ref: str = Field(min_length=1)


class ConversationGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)
    target_phrases: list[str] = Field(default_factory=list, max_length=3)


class LessonPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["A1", "A2", "B1"]
    source: Source
    new_words: list[str] = Field(default_factory=list, max_length=3)
    conversation_goals: list[ConversationGoal] = Field(min_length=1, max_length=4)
    weak_items: list[str] = Field(default_factory=list, max_length=20)
