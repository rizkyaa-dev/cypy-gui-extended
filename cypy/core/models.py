from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    def as_list(self):
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass(frozen=True)
class Bubble:
    bubble_id: str
    box: Box
    crop: Any


@dataclass(frozen=True)
class TranslationResult:
    bubble_id: str
    text: str
