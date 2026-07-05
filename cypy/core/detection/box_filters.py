import os

import cv2
import numpy as np

from cypy.core.settings import ProcessingSettings


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


def _area_box(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def _irisan_box(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    return max(0, ix2 - ix1) * max(0, iy2 - iy1)


def _perlu_digabung(a, b):
    area_a = _area_box(a)
    area_b = _area_box(b)

    if area_a == 0 or area_b == 0:
        return False

    inter = _irisan_box(a, b)
    if inter == 0:
        return False

    iou = inter / float(area_a + area_b - inter)
    cover_kotak_kecil = inter / float(min(area_a, area_b))

    return iou >= 0.28 or cover_kotak_kecil >= 0.82


def buang_kotak_raksasa_palsu(boxes, settings=None):
    if not boxes:
        return []

    boxes_with_area = [(box, _area_box(box)) for box in boxes]
    boxes_with_area.sort(key=lambda item: item[1], reverse=True)
    keep = [True] * len(boxes_with_area)

    for i, (box_i, area_i) in enumerate(boxes_with_area):
        if not keep[i]:
            continue

        for j in range(i + 1, len(boxes_with_area)):
            if not keep[j]:
                continue

            box_j, area_j = boxes_with_area[j]
            if area_i > 2.5 * area_j and _irisan_box(box_i, box_j) >= 0.8 * area_j:
                keep[i] = False
                break

    return [boxes_with_area[i][0] for i in range(len(boxes_with_area)) if keep[i]]


def gabung_kotak_tumpang_tindih(boxes, settings=None):
    if not boxes:
        return []

    boxes = [list(map(int, box)) for box in boxes]
    berubah = True

    while berubah:
        berubah = False
        hasil = []
        dipakai = [False] * len(boxes)

        for i, box in enumerate(boxes):
            if dipakai[i]:
                continue

            x1, y1, x2, y2 = box

            for j in range(i + 1, len(boxes)):
                if dipakai[j]:
                    continue

                if _perlu_digabung([x1, y1, x2, y2], boxes[j]):
                    ox1, oy1, ox2, oy2 = boxes[j]
                    x1 = min(x1, ox1)
                    y1 = min(y1, oy1)
                    x2 = max(x2, ox2)
                    y2 = max(y2, oy2)
                    dipakai[j] = True
                    berubah = True

            hasil.append([x1, y1, x2, y2])
            dipakai[i] = True

        boxes = hasil

    return sorted(boxes, key=lambda box: (box[1], box[0]))


def buang_kotak_ngawur(boxes, lebar_img, tinggi_img, settings=None):
    hasil = []
    luas_gambar = max(1, lebar_img * tinggi_img)

    for box in boxes:
        x1, y1, x2, y2 = box
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        ratio = width / float(height)
        area_ratio = (width * height) / float(luas_gambar)

        terlalu_lebar = ratio >= 3.2 and width >= lebar_img * 0.35
        terlalu_gepeng_besar = width >= lebar_img * 0.50 and height <= tinggi_img * 0.16
        terlalu_besar_tipis = area_ratio >= 0.035 and ratio >= 2.8

        if terlalu_lebar or terlalu_gepeng_besar or terlalu_besar_tipis:
            continue

        hasil.append(box)

    return hasil


def simpan_debug_crop_filter(image_name, crop, box, alasan, settings=None):
    cfg = _settings(settings)
    if not cfg.simpan_debug_filter_sfx:
        return

    debug_dir = os.path.join(cfg.root_dir, "cypy_cache", "debug_filter_sfx")
    os.makedirs(debug_dir, exist_ok=True)

    safe_name = os.path.basename(image_name).replace(".", "_")
    x1, y1, x2, y2 = box
    path = os.path.join(debug_dir, f"{safe_name}_{alasan}_{x1}_{y1}_{x2}_{y2}.png")

    try:
        cv2.imwrite(path, crop)
    except Exception:
        pass


def buang_kotak_sfx_dan_gambar(img, boxes, image_name="image", settings=None):
    cfg = _settings(settings)
    if not cfg.filter_sfx_aktif:
        return boxes

    hasil = []
    tinggi_img, lebar_img = img.shape[:2]
    luas_img = max(1, tinggi_img * lebar_img)

    if cfg.filter_sfx_mode == "longgar":
        black_thr = 0.20
        edge_thr = 0.14
        white_safe = 0.58
    elif cfg.filter_sfx_mode == "ketat":
        black_thr = 0.13
        edge_thr = 0.09
        white_safe = 0.68
    else:
        black_thr = 0.16
        edge_thr = 0.11
        white_safe = 0.62

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        area_ratio = (width * height) / float(luas_img)
        ratio = width / float(height)
        crop = img[y1:y2, x1:x2]

        if crop.size == 0:
            continue

        box_kecil = (
            width < lebar_img * 0.18
            and height < tinggi_img * 0.18
            and area_ratio < 0.020
        )
        if box_kecil:
            hasil.append(box)
            continue

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        black_ratio = float(np.mean(gray < 80))
        white_ratio = float(np.mean(gray > 220))
        edges = cv2.Canny(gray, 80, 160)
        edge_ratio = float(np.mean(edges > 0))

        if white_ratio >= white_safe:
            hasil.append(box)
            continue

        sfx_atau_gambar = (
            area_ratio > 0.018
            and black_ratio > black_thr
            and edge_ratio > edge_thr
        )
        gepeng_mencurigakan = (
            ratio > 2.2
            and width > lebar_img * 0.30
            and edge_ratio > max(0.07, edge_thr - 0.03)
            and white_ratio < white_safe
        )
        gambar_besar_mencurigakan = (
            area_ratio > 0.045
            and white_ratio < 0.55
            and edge_ratio > 0.075
        )

        if sfx_atau_gambar or gepeng_mencurigakan or gambar_besar_mencurigakan:
            simpan_debug_crop_filter(image_name, crop, box, "sfx", settings=cfg)
            continue

        hasil.append(box)

    return hasil


__all__ = [
    "_area_box",
    "_irisan_box",
    "buang_kotak_ngawur",
    "buang_kotak_raksasa_palsu",
    "buang_kotak_sfx_dan_gambar",
    "gabung_kotak_tumpang_tindih",
    "simpan_debug_crop_filter",
]
