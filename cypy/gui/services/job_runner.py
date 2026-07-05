from dataclasses import dataclass
from typing import Any, Callable

from cypy.core.documents.image_processor import proses_satu_gambar
from cypy.core.reporting import ensure_reporter
from cypy.gui.models.job import JobStatus, ProcessingResult


@dataclass(frozen=True)
class GuiProcessingContext:
    yolo_model: Any
    provider: Any
    target_language: str
    settings: Any
    provider_lock: Any = None
    detector: Any = None


class JobRunner:
    """Runs one GUI job through the existing core processing pipeline."""

    def __init__(self, processor: Callable = proses_satu_gambar):
        self.processor = processor

    def run(self, job, context, reporter=None):
        reporter = ensure_reporter(reporter)
        running_job = job.with_status(JobStatus.RUNNING, "Processing", progress=0)

        try:
            output_path = self.processor(
                running_job.input_path,
                context.yolo_model,
                provider=context.provider,
                target_language=context.target_language,
                settings=context.settings,
                reporter=reporter,
                provider_lock=context.provider_lock,
                detector=context.detector,
            )
        except Exception as exc:
            failed = running_job.with_status(JobStatus.FAILED, str(exc), progress=100)
            return ProcessingResult(
                job=failed,
                output_path=None,
                success=False,
                error=str(exc),
            )

        if output_path:
            succeeded = running_job.with_status(
                JobStatus.SUCCEEDED,
                "Completed",
                progress=100,
                output_path=output_path,
            )
            return ProcessingResult(job=succeeded, output_path=output_path, success=True)

        failed = running_job.with_status(JobStatus.FAILED, "Processing failed", progress=100)
        return ProcessingResult(
            job=failed,
            output_path=None,
            success=False,
            error="Processing failed",
        )
