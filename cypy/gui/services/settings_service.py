import os
import threading
from dataclasses import dataclass

import cypy.core.config as config
from cypy.core.detection.detector import YoloBubbleDetector
from cypy.core.detection.yolo_onnx import YOLOONNX
from cypy.core.providers.factory import create_provider
from cypy.core.settings import ProcessingSettings, get_provider_settings


@dataclass(frozen=True)
class GuiProviderConfig:
    name: str
    api_key: str
    model_name: str
    base_url: str = ""


class GuiSettingsService:
    """Small bridge between GUI state and legacy config-backed settings."""

    def __init__(self, provider_factory=create_provider, yolo_factory=YOLOONNX):
        self.provider_factory = provider_factory
        self.yolo_factory = yolo_factory
        self.provider_lock = threading.Lock()
        self.yolo_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._detector_lock = threading.Lock()
        self._yolo_model = None
        self._bubble_detector = None

    def processing_settings(self):
        return ProcessingSettings.from_config()

    def target_language(self):
        return config.TARGET_LANGUAGE or "Indonesian"

    def provider_config(self):
        provider = get_provider_settings()
        return GuiProviderConfig(
            name=provider.name,
            api_key=provider.api_key,
            model_name=provider.model_name,
            base_url=provider.base_url,
        )

    def create_provider(self, provider_config=None):
        provider_config = provider_config or self.provider_config()
        kwargs = {}
        if provider_config.name == "custom":
            kwargs["base_url"] = provider_config.base_url
        return self.provider_factory(
            provider_config.name,
            api_key=provider_config.api_key,
            model_name=provider_config.model_name,
            **kwargs,
        )

    def create_yolo_model(self):
        if self._yolo_model is not None:
            return self._yolo_model

        with self._model_lock:
            if self._yolo_model is not None:
                return self._yolo_model

            if not os.path.exists(config.MODEL_YOLO):
                raise FileNotFoundError(
                    f"YOLO model file not found: {config.MODEL_YOLO}"
                )

            self._yolo_model = self.yolo_factory(config.MODEL_YOLO)
            return self._yolo_model

    def create_bubble_detector(self):
        if self._bubble_detector is not None:
            return self._bubble_detector

        with self._detector_lock:
            if self._bubble_detector is None:
                self._bubble_detector = YoloBubbleDetector(
                    self.create_yolo_model(),
                    lock=self.yolo_lock,
                )
        return self._bubble_detector
