from cypy.gui.services.detection_service import BubbleDetectionService
from cypy.gui.services.job_runner import GuiProcessingContext, JobRunner
from cypy.gui.services.settings_service import GuiSettingsService
from cypy.core.detection.detector import PrecomputedBubbleDetector


class GuiAppController:
    def __init__(self, settings_service=None, job_runner=None):
        self.settings_service = settings_service or GuiSettingsService()
        self.job_runner = job_runner or JobRunner()
        self._detection_service = None

    def supported_image_extensions(self):
        return self.settings_service.processing_settings().supported_image_extensions

    def default_target_language(self):
        return self.settings_service.target_language()

    def create_processing_context(self, target_language=None, detected_boxes=None):
        settings = self.settings_service.processing_settings()
        provider = self.settings_service.create_provider()
        yolo_model = self.settings_service.create_yolo_model()

        detector = (
            PrecomputedBubbleDetector(box.as_list() for box in detected_boxes)
            if detected_boxes is not None
            else self.settings_service.create_bubble_detector()
        )

        return GuiProcessingContext(
            yolo_model=yolo_model,
            provider=provider,
            target_language=target_language or self.settings_service.target_language(),
            settings=settings,
            provider_lock=self.settings_service.provider_lock,
            detector=detector,
        )

    def detect_bubbles(self, image_path):
        if self._detection_service is None:
            self._detection_service = BubbleDetectionService(
                self.settings_service.create_bubble_detector(),
                self.settings_service.processing_settings(),
            )
        return self._detection_service.detect_preview(image_path)
