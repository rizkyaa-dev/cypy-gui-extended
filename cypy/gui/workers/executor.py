from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Lock

from cypy.gui.events import GuiEvent, GuiEventType
from cypy.gui.models.job import JobStatus, ProcessingResult
from cypy.gui.reporters.queue_reporter import QueueReporter


class ProcessingExecutor:
    """Runs processing jobs and publishes immutable events for the UI thread."""

    def __init__(self, job_runner, event_queue=None, max_workers=3):
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        self.job_runner = job_runner
        self.event_queue = event_queue or Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="cypy-gui",
        )
        self._futures = set()
        self._lock = Lock()
        self._closed = False

    def submit(self, job, context):
        with self._lock:
            if self._closed:
                raise RuntimeError("Processing executor is closed")
            future = self._executor.submit(self._run_job, job, context)
            self._futures.add(future)
        future.add_done_callback(self._discard_future)
        return future

    def shutdown(self, wait=False):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            futures = tuple(self._futures)

        for future in futures:
            future.cancel()
        self._executor.shutdown(wait=wait)

    def _run_job(self, job, context):
        running_job = job.with_status(JobStatus.RUNNING, "Processing", progress=0)
        self.event_queue.put(
            GuiEvent(GuiEventType.JOB_STARTED, job_id=job.id, payload=running_job)
        )

        reporter = QueueReporter(self.event_queue, job_id=job.id)
        try:
            result = self.job_runner.run(job, context, reporter=reporter)
        except Exception as exc:
            failed_job = running_job.with_status(
                JobStatus.FAILED,
                str(exc),
                progress=100,
            )
            result = ProcessingResult(
                job=failed_job,
                output_path=None,
                success=False,
                error=str(exc),
            )
            self.event_queue.put(
                GuiEvent(
                    GuiEventType.JOB_FAILED,
                    job_id=job.id,
                    payload=result,
                    message=str(exc),
                )
            )
            return result

        event_type = (
            GuiEventType.JOB_FINISHED if result.success else GuiEventType.JOB_FAILED
        )
        self.event_queue.put(
            GuiEvent(
                event_type,
                job_id=job.id,
                payload=result,
                message=result.error,
            )
        )
        return result

    def _discard_future(self, future):
        with self._lock:
            self._futures.discard(future)
