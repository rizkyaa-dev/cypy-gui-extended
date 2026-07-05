from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from cypy.gui.events import GuiEvent, GuiEventType
from cypy.gui.models.job import DetectionResult


class DetectionExecutor:
    """Runs bubble detection without blocking Tk's event loop."""

    def __init__(self, detector, event_queue):
        self.detector = detector
        self.event_queue = event_queue
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cypy-detection",
        )
        self._futures = set()
        self._lock = Lock()
        self._closed = False

    def submit(self, job):
        with self._lock:
            if self._closed:
                raise RuntimeError("Detection executor is closed")
            future = self._executor.submit(self._detect, job)
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

    def _detect(self, job):
        self.event_queue.put(
            GuiEvent(GuiEventType.DETECTION_STARTED, job_id=job.id)
        )
        try:
            boxes = self.detector(job.input_path)
        except Exception as exc:
            result = DetectionResult(job_id=job.id, boxes=(), error=str(exc))
            self.event_queue.put(
                GuiEvent(
                    GuiEventType.DETECTION_FAILED,
                    job_id=job.id,
                    payload=result,
                    message=str(exc),
                )
            )
            return result

        result = DetectionResult(job_id=job.id, boxes=tuple(boxes))
        self.event_queue.put(
            GuiEvent(
                GuiEventType.DETECTION_FINISHED,
                job_id=job.id,
                payload=result,
            )
        )
        return result

    def _discard_future(self, future):
        with self._lock:
            self._futures.discard(future)

