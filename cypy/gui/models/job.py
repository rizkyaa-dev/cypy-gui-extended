import os
import uuid
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional, Tuple

from cypy.core.models import Box, TextSegmentationMask


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class DetectionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ProcessingJob:
    input_path: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    output_path: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    message: str = ""
    boxes: Tuple[Box, ...] = field(default_factory=tuple)
    text_mask: Optional[TextSegmentationMask] = None
    detection_status: DetectionStatus = DetectionStatus.PENDING
    detection_error: str = ""

    @property
    def filename(self):
        return os.path.basename(self.input_path)

    def with_status(self, status, message="", progress=None, output_path=None):
        return replace(
            self,
            status=JobStatus(status),
            message=message,
            progress=self.progress if progress is None else int(progress),
            output_path=self.output_path if output_path is None else output_path,
        )

    def reset(self):
        return replace(
            self,
            status=JobStatus.PENDING,
            progress=0,
            message="",
            output_path=None,
        )

    def with_detection(self, status, boxes=None, error="", text_mask=None):
        return replace(
            self,
            boxes=self.boxes if boxes is None else tuple(boxes),
            text_mask=text_mask,
            detection_status=DetectionStatus(status),
            detection_error=str(error),
        )


@dataclass(frozen=True)
class ProcessingResult:
    job: ProcessingJob
    output_path: Optional[str]
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class DetectionResult:
    job_id: str
    boxes: Tuple[Box, ...]
    text_mask: Optional[TextSegmentationMask] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class DetectionPreview:
    boxes: Tuple[Box, ...]
    text_mask: Optional[TextSegmentationMask] = None


class JobQueue:
    def __init__(self, jobs=None):
        self._jobs = list(jobs or [])

    def __len__(self):
        return len(self._jobs)

    def __iter__(self):
        return iter(self._jobs)

    def __getitem__(self, index):
        return self._jobs[index]

    @property
    def jobs(self):
        return list(self._jobs)

    def add_paths(self, paths):
        existing = {os.path.normcase(os.path.abspath(job.input_path)) for job in self._jobs}
        added = []

        for path in paths:
            normalized = os.path.abspath(str(path))
            key = os.path.normcase(normalized)
            if key in existing:
                continue

            job = ProcessingJob(input_path=normalized)
            self._jobs.append(job)
            existing.add(key)
            added.append(job)

        return added

    def clear_finished(self):
        self._jobs = [
            job
            for job in self._jobs
            if job.status not in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED)
        ]

    def pending_jobs(self):
        return [job for job in self._jobs if job.status == JobStatus.PENDING]

    def get(self, job_id):
        for job in self._jobs:
            if job.id == job_id:
                return job
        raise KeyError(f"Unknown job id: {job_id}")

    def remove(self, job_id):
        for index, job in enumerate(self._jobs):
            if job.id == job_id:
                return self._jobs.pop(index)
        raise KeyError(f"Unknown job id: {job_id}")

    def update(self, updated_job):
        for index, job in enumerate(self._jobs):
            if job.id == updated_job.id:
                self._jobs[index] = updated_job
                return index
        raise KeyError(f"Unknown job id: {updated_job.id}")
