import os
from dataclasses import dataclass

import cypy.core.config as config


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    api_key: str
    model_name: str
    base_url: str = ""


@dataclass(frozen=True)
class AppSettings:
    provider: ProviderSettings
    target_language: str
    model_yolo: str
    font_manga: str


@dataclass(frozen=True)
class ProcessingSettings:
    root_dir: str
    assets_dir: str
    cache_dir: str
    supported_image_extensions: tuple
    font_manga: str
    font_japanese: str
    max_tinggi_mosaik: int
    margin_kiri_nomor: int
    margin_kanan: int
    jarak_antar_potongan: int
    lebar_mosaik_min: int
    min_pad: int
    pad_x_ratio: float
    pad_y_ratio: float
    skala_potongan_mosaik: float
    overlap_batas_crop: float
    mask_area_luar_box: bool
    mask_margin: int
    mask_margin_ratio: float
    filter_sfx_aktif: bool
    filter_sfx_mode: str
    simpan_debug_filter_sfx: bool
    text_assist_enabled: bool
    text_detector_model: str
    text_assist_min_score: float
    text_assist_box_threshold: float
    text_assist_expand_margin: int
    text_assist_orphan_recovery: bool
    pakai_patch_untuk_box_gepeng: bool
    rasio_box_gepeng: float
    lebar_box_gepeng_ratio: float
    tinggi_box_gepeng_ratio: float
    manual_translation_override: dict
    lang_codes: dict

    @classmethod
    def from_config(cls):
        cache_dir = getattr(config, "CACHE_DIR", None) or config.ROOT_DIR
        return cls(
            root_dir=config.ROOT_DIR,
            assets_dir=config.ASSETS_DIR,
            cache_dir=cache_dir,
            supported_image_extensions=config.SUPPORTED_IMAGE_EXTENSIONS,
            font_manga=config.FONT_MANGA,
            font_japanese=os.path.join(config.ASSETS_DIR, "KosugiMaru.ttf"),
            max_tinggi_mosaik=config.MAX_TINGGI_MOSAIK,
            margin_kiri_nomor=config.MARGIN_KIRI_NOMOR,
            margin_kanan=config.MARGIN_KANAN,
            jarak_antar_potongan=config.JARAK_ANTAR_POTONGAN,
            lebar_mosaik_min=config.LEBAR_MOSAIK_MIN,
            min_pad=config.MIN_PAD,
            pad_x_ratio=config.PAD_X_RATIO,
            pad_y_ratio=config.PAD_Y_RATIO,
            skala_potongan_mosaik=config.SKALA_POTONGAN_MOSAIK,
            overlap_batas_crop=config.OVERLAP_BATAS_CROP,
            mask_area_luar_box=config.MASK_AREA_LUAR_BOX,
            mask_margin=config.MASK_MARGIN,
            mask_margin_ratio=config.MASK_MARGIN_RATIO,
            filter_sfx_aktif=config.FILTER_SFX_AKTIF,
            filter_sfx_mode=config.FILTER_SFX_MODE,
            simpan_debug_filter_sfx=config.SIMPAN_DEBUG_FILTER_SFX,
            text_assist_enabled=config.TEXT_ASSIST_ENABLED,
            text_detector_model=config.MODEL_TEXT_DETECTOR,
            text_assist_min_score=config.TEXT_ASSIST_MIN_SCORE,
            text_assist_box_threshold=config.TEXT_ASSIST_BOX_THRESHOLD,
            text_assist_expand_margin=config.TEXT_ASSIST_EXPAND_MARGIN,
            text_assist_orphan_recovery=config.TEXT_ASSIST_ORPHAN_RECOVERY,
            pakai_patch_untuk_box_gepeng=config.PAKAI_PATCH_UNTUK_BOX_GEPENG,
            rasio_box_gepeng=config.RASIO_BOX_GEPENG,
            lebar_box_gepeng_ratio=config.LEBAR_BOX_GEPENG_RATIO,
            tinggi_box_gepeng_ratio=config.TINGGI_BOX_GEPENG_RATIO,
            manual_translation_override=dict(config.MANUAL_TRANSLATION_OVERRIDE),
            lang_codes=dict(config.LANG_CODES),
        )


def get_provider_settings(provider_name=None):
    name = (provider_name or config.LLM_PROVIDER or "gemini").lower()
    api_key, model_name = config.get_provider_config(name)
    base_url = config.CUSTOM_BASE_URL if name == "custom" else ""

    return ProviderSettings(
        name=name,
        api_key=api_key,
        model_name=model_name,
        base_url=base_url,
    )


def get_app_settings():
    return AppSettings(
        provider=get_provider_settings(),
        target_language=config.TARGET_LANGUAGE,
        model_yolo=config.MODEL_YOLO,
        font_manga=config.FONT_MANGA,
    )


def load_settings():
    return config.load_settings()


def save_settings():
    return config.save_settings()


def load_local_profile():
    return config.load_local_profile()


def save_local_profile():
    return config.save_local_profile()
