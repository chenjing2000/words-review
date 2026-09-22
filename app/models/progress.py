from dataclasses import dataclass, field
from enum import IntEnum


class StudyStatus(IntEnum):
    UNLEARNED = 0
    UNCERTAIN = 1
    RECOGNIZED = 2
    MASTERED = 3


class ReviewMode(IntEnum):
    ALL = -1
    UNLEARNED = 0
    UNCERTAIN = 1
    RECOGNIZED = 2
    MASTERED = 3


@dataclass
class WordProgress:
    review_count: int = 0
    study_status: StudyStatus = StudyStatus.UNLEARNED


@dataclass
class ReviewSessionState:
    mode: ReviewMode = ReviewMode.ALL
    queue_position: int = 0
    indices: list[int] = field(default_factory=list)
    completed: bool = False


@dataclass
class WordListProgress:
    schema_version: int = 1
    current_index: int = 0
    review_session: ReviewSessionState = field(default_factory=ReviewSessionState)
    words: dict[str, WordProgress] = field(default_factory=dict)
