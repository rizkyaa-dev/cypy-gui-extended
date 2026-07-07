import tkinter as tk
from tkinter import ttk

import numpy as np
from PIL import Image, ImageTk


class PreviewPanel(ttk.Frame):
    def __init__(self, parent, title="Preview"):
        super().__init__(parent, style="Viewer.TFrame")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text=title.upper(),
            anchor=tk.CENTER,
            style="ViewerHeader.TLabel",
        ).grid(row=0, column=0, sticky="ew")
        self.canvas = tk.Canvas(
            self,
            background="#101010",
            highlightbackground="#353535",
            highlightcolor="#353535",
            highlightthickness=1,
            width=420,
            height=520,
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._schedule_refresh)

        self._source_image = None
        self._photo_image = None
        self._boxes = ()
        self._text_mask = None
        self._message = "No image selected"
        self._refresh_pending = False
        self._refresh()

    def set_image_path(self, path, boxes=None, text_mask=None):
        try:
            with Image.open(path) as image:
                self._source_image = image.convert("RGB").copy()
        except (OSError, ValueError):
            self.clear("Unable to load image")
        else:
            self._boxes = tuple(boxes or ())
            self._text_mask = text_mask
            self._message = ""
            self._refresh()

    def set_boxes(self, boxes):
        self._boxes = tuple(boxes or ())
        self._refresh()

    def clear(self, message="No image selected"):
        self._source_image = None
        self._photo_image = None
        self._boxes = ()
        self._text_mask = None
        self._message = message
        self._refresh()

    def _schedule_refresh(self, event=None):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self.after_idle(self._refresh)

    def _refresh(self):
        self._refresh_pending = False
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())

        if self._source_image is None:
            self.canvas.create_text(
                width // 2,
                height // 2,
                text=self._message,
                fill="#9b9b9b",
                font=("Segoe UI", 10),
            )
            return

        source_width, source_height = self._source_image.size
        scale = min(width / source_width, height / source_height)
        target_size = (
            max(1, int(source_width * scale)),
            max(1, int(source_height * scale)),
        )
        resampling = getattr(Image, "Resampling", Image)
        resized = self._source_image.resize(target_size, resampling.LANCZOS)
        resized = self._apply_text_mask_overlay(resized, target_size)
        self._photo_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(
            width // 2,
            height // 2,
            image=self._photo_image,
            anchor=tk.CENTER,
        )
        self._draw_boxes(width, height, target_size, scale)

    def _apply_text_mask_overlay(self, image, target_size):
        if self._text_mask is None:
            return image

        mask = np.asarray(self._text_mask.mask, dtype=np.uint8)
        if mask.ndim != 2 or not np.any(mask):
            return image

        source_width, source_height = self._source_image.size
        if (
            int(self._text_mask.width) != source_width
            or int(self._text_mask.height) != source_height
        ):
            return image

        resampling = getattr(Image, "Resampling", Image)
        mask_image = Image.fromarray(mask).resize(
            target_size,
            resampling.NEAREST,
        )
        alpha = mask_image.point(lambda value: 88 if value > 0 else 0)
        overlay = Image.new("RGBA", target_size, (0, 190, 255, 0))
        overlay.putalpha(alpha)
        return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    def _draw_boxes(self, canvas_width, canvas_height, target_size, scale):
        if not self._boxes:
            return

        image_left = (canvas_width - target_size[0]) / 2
        image_top = (canvas_height - target_size[1]) / 2
        source_width, source_height = self._source_image.size

        for index, box in enumerate(self._boxes, start=1):
            x1 = max(0, min(source_width, int(box.x1)))
            y1 = max(0, min(source_height, int(box.y1)))
            x2 = max(0, min(source_width, int(box.x2)))
            y2 = max(0, min(source_height, int(box.y2)))
            if x2 <= x1 or y2 <= y1:
                continue

            left = image_left + (x1 * scale)
            top = image_top + (y1 * scale)
            right = image_left + (x2 * scale)
            bottom = image_top + (y2 * scale)
            self.canvas.create_rectangle(
                left,
                top,
                right,
                bottom,
                outline="#ef5961",
                width=2,
            )

            label = str(index)
            badge_size = 20 if len(label) == 1 else 24
            badge_left = max(image_left, left - 1)
            badge_top = max(image_top, top - badge_size)
            self.canvas.create_rectangle(
                badge_left,
                badge_top,
                badge_left + badge_size,
                badge_top + 20,
                fill="#d92532",
                outline="#d92532",
            )
            self.canvas.create_text(
                badge_left + (badge_size / 2),
                badge_top + 10,
                text=label,
                fill="#ffffff",
                font=("Segoe UI Semibold", 9),
            )
