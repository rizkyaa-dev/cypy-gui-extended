def test_legacy_facade_imports():
    from cypy.core import translator, utils, yolo_onnx

    assert translator.proses_satu_gambar
    assert utils.bersihkan_json_dari_gemini
    assert yolo_onnx.YOLOONNX


def test_new_module_imports():
    from cypy.core import detection, documents, imaging, translation
    from cypy.core.imaging.fonts import FontResolver
    from cypy.core.providers.factory import create_provider

    assert detection.YOLOONNX
    assert documents.OutputNamer
    assert documents.proses_satu_gambar
    assert imaging.build_numbered_mosaic
    assert translation.MosaicTranslationService
    assert translation.ProviderCallGuard
    assert translation.RetryPolicy
    assert FontResolver
    assert create_provider
