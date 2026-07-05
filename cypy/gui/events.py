from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class GuiEventType(str, Enum):
    DETECTION_STARTED = "detection_started"
    DETECTION_FINISHED = "detection_finished"
    DETECTION_FAILED = "detection_failed"
    JOB_STARTED = "job_started"
    JOB_FINISHED = "job_finished"
    JOB_FAILED = "job_failed"
    LOG = "log"


@dataclass(frozen=True)
class GuiEvent:
    type: GuiEventType
    job_id: Optional[str] = None
    payload: Any = None
    level: Optional[str] = None
    message: Optional[str] = None
