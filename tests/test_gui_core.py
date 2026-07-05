import queue

import numpy as np

from cypy.core.models import Box
from cypy.gui.events import GuiEventType
from cypy.gui.models.job import (
    DetectionStatus,
    JobQueue,
    JobStatus,
    ProcessingJob,
)
from cypy.gui.reporters.queue_reporter import QueueReporter
from cypy.gui.services.app_controller import GuiAppController
from cypy.gui.services.detection_service import BubbleDetectionService
from cypy.gui.services.job_runner import GuiProcessingContext, JobRunner
from cypy.gui.workers.detection_executor import DetectionExecutor
from cypy.gui.workers.executor import ProcessingExecutor


def test_job_queue_adds_unique_absolute_paths(tmp_path):
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    first.write_text("x")
    second.write_text("x")

    queue = JobQueue()
    added = queue.add_paths([first, first, second])

    assert len(added) == 2
    assert len(queue) == 2
    assert queue[0].filename == "a.png"
    assert queue[1].filename == "b.png"


def test_job_queue_update_and_pending_filter(tmp_path):
    path = tmp_path / "a.png"
    path.write_text("x")
    queue = JobQueue()
    job = queue.add_paths([path])[0]

    updated = job.with_status(JobStatus.SUCCEEDED, "done", progress=100, output_path="out.png")
    row = queue.update(updated)

    assert row == 0
    assert queue[0].status == JobStatus.SUCCEEDED
    assert queue.pending_jobs() == []


def test_job_can_be_reset_and_removed(tmp_path):
    path = tmp_path / "a.png"
    path.write_text("x")
    jobs = JobQueue()
    job = jobs.add_paths([path])[0]
    completed = job.with_status(
        JobStatus.SUCCEEDED,
        "done",
        progress=100,
        output_path="output.png",
    )

    reset = completed.reset()
    jobs.update(reset)
    removed = jobs.remove(reset.id)

    assert reset.status == JobStatus.PENDING
    assert reset.progress == 0
    assert reset.output_path is None
    assert removed.id == job.id
    assert len(jobs) == 0


def test_job_stores_immutable_detection_result(tmp_path):
    job = ProcessingJob(str(tmp_path / "page.png"))
    boxes = [Box(1, 2, 30, 40)]

    detected = job.with_detection(DetectionStatus.SUCCEEDED, boxes=boxes)
    boxes.append(Box(5, 6, 7, 8))

    assert detected.detection_status == DetectionStatus.SUCCEEDED
    assert detected.boxes == (Box(1, 2, 30, 40),)


def test_controller_applies_gui_target_language_override():
    class FakeSettingsService:
        provider_lock = "lock"

        def processing_settings(self):
            return "settings"

        def create_provider(self):
            return "provider"

        def create_yolo_model(self):
            return "yolo"

        def target_language(self):
            return "Indonesian"

        def create_bubble_detector(self):
            return "detector"

    controller = GuiAppController(settings_service=FakeSettingsService())

    context = controller.create_processing_context(target_language="English")

    assert context.target_language == "English"
    assert context.provider_lock == "lock"
    assert context.detector == "detector"


def test_controller_reuses_preview_detection_boxes():
    class FakeSettingsService:
        provider_lock = "lock"

        def processing_settings(self):
            return "settings"

        def create_provider(self):
            return "provider"

        def create_yolo_model(self):
            return "yolo"

        def target_language(self):
            return "Indonesian"

        def create_bubble_detector(self):
            raise AssertionError("live detector should not be requested")

    controller = GuiAppController(settings_service=FakeSettingsService())
    context = controller.create_processing_context(
        detected_boxes=(Box(1, 2, 30, 40),)
    )

    assert context.detector.detect(None) == [[1, 2, 30, 40]]


def test_detection_service_returns_typed_boxes(monkeypatch):
    class FakePipeline:
        def detect_boxes(self, image, image_path):
            assert image.shape == (20, 30, 3)
            assert image_path == "page.png"
            return [[1, 2, 10, 12], [15, 4, 25, 18]]

    monkeypatch.setattr(
        "cypy.gui.services.detection_service.cv2.imread",
        lambda path: np.zeros((20, 30, 3), dtype=np.uint8),
    )
    service = BubbleDetectionService(None, None, pipeline=FakePipeline())

    boxes = service.detect("page.png")

    assert boxes == (Box(1, 2, 10, 12), Box(15, 4, 25, 18))


def test_job_runner_success_passes_context_to_processor(tmp_path):
    input_path = tmp_path / "a.png"
    output_path = tmp_path / "a_cypytr_id.png"
    input_path.write_text("x")
    output_path.write_text("out")
    calls = {}

    def fake_processor(image_path, yolo_model, **kwargs):
        calls["image_path"] = image_path
        calls["yolo_model"] = yolo_model
        calls.update(kwargs)
        return str(output_path)

    runner = JobRunner(processor=fake_processor)
    job = ProcessingJob(str(input_path))
    context = GuiProcessingContext(
        yolo_model="yolo",
        provider="provider",
        target_language="Indonesian",
        settings="settings",
        provider_lock="lock",
    )

    result = runner.run(job, context)

    assert result.success is True
    assert result.job.status == JobStatus.SUCCEEDED
    assert result.output_path == str(output_path)
    assert calls["provider"] == "provider"
    assert calls["provider_lock"] == "lock"


def test_job_runner_failure_returns_failed_result(tmp_path):
    def fake_processor(*args, **kwargs):
        raise RuntimeError("boom")

    runner = JobRunner(processor=fake_processor)
    job = ProcessingJob(str(tmp_path / "a.png"))
    context = GuiProcessingContext(
        yolo_model=None,
        provider=None,
        target_language="Indonesian",
        settings=None,
    )

    result = runner.run(job, context)

    assert result.success is False
    assert result.job.status == JobStatus.FAILED
    assert result.error == "boom"


def test_queue_reporter_publishes_log_event():
    events = queue.Queue()
    reporter = QueueReporter(events, job_id="job-1")

    reporter.warning("check this")

    event = events.get_nowait()
    assert event.type == GuiEventType.LOG
    assert event.job_id == "job-1"
    assert event.level == "warning"
    assert event.message == "check this"


def test_processing_executor_publishes_lifecycle_events(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    input_path.write_text("input")
    output_path.write_text("output")

    def fake_processor(*args, **kwargs):
        kwargs["reporter"].info("working")
        return str(output_path)

    events = queue.Queue()
    executor = ProcessingExecutor(
        JobRunner(processor=fake_processor),
        event_queue=events,
        max_workers=1,
    )
    job = ProcessingJob(str(input_path))
    context = GuiProcessingContext(None, None, "Indonesian", None)

    try:
        result = executor.submit(job, context).result(timeout=2)
    finally:
        executor.shutdown(wait=True)

    event_types = []
    while not events.empty():
        event_types.append(events.get_nowait().type)

    assert result.success is True
    assert event_types == [
        GuiEventType.JOB_STARTED,
        GuiEventType.LOG,
        GuiEventType.JOB_FINISHED,
    ]


def test_detection_executor_publishes_boxes(tmp_path):
    events = queue.Queue()
    executor = DetectionExecutor(
        lambda path: (Box(1, 2, 30, 40),),
        event_queue=events,
    )
    job = ProcessingJob(str(tmp_path / "page.png"))

    try:
        result = executor.submit(job).result(timeout=2)
    finally:
        executor.shutdown(wait=True)

    assert result.boxes == (Box(1, 2, 30, 40),)
    assert [events.get_nowait().type, events.get_nowait().type] == [
        GuiEventType.DETECTION_STARTED,
        GuiEventType.DETECTION_FINISHED,
    ]
