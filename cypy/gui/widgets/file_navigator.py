import os
import queue
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from tkinter import ttk

from PIL import Image, ImageTk

from cypy.gui.models.job import DetectionStatus, JobStatus


@dataclass(frozen=True)
class ThumbnailResult:
    job_id: str
    cache_key: tuple
    image: Image.Image


class FileNavigator(ttk.Frame):
    CARD_WIDTH = 176
    CARD_HEIGHT = 228
    CARD_GAP = 10
    SCROLLBAR_WIDTH = 10
    THUMBNAIL_SIZE = (132, 172)
    VIEWPORT_BUFFER = 3
    THUMBNAIL_WORKERS = 2

    def __init__(self, parent, on_select):
        super().__init__(parent, style="Navigator.TFrame")
        self.on_select = on_select
        self._jobs = ()
        self._job_by_id = {}
        self._selected_index = -1
        self._photo_cache = {}
        self._pil_cache = {}
        self._pending_thumbnails = set()
        self._thumbnail_results = queue.Queue()
        self._thumbnail_executor = ThreadPoolExecutor(
            max_workers=self.THUMBNAIL_WORKERS,
            thread_name_prefix="cypy-thumbnails",
        )
        self._thumbnail_poll_after_id = None
        self._render_after_id = None
        self._placeholder = None
        self.count_var = tk.StringVar(value="0 pages")

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_header()
        self.canvas = tk.Canvas(
            self,
            background="#121212",
            borderwidth=0,
            highlightthickness=0,
            width=196,
        )
        self.scrollbar = tk.Canvas(
            self,
            background="#121212",
            borderwidth=0,
            highlightthickness=0,
            width=self.SCROLLBAR_WIDTH,
        )
        self.canvas.configure(yscrollcommand=self._on_canvas_scroll)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.scrollbar.bind("<Button-1>", self._on_scrollbar_click)
        self.scrollbar.bind("<B1-Motion>", self._on_scrollbar_drag)
        self.scrollbar.bind("<Configure>", lambda event: self._draw_scrollbar())
        self.scrollbar.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._schedule_render)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-1>", self._on_click)

        self._schedule_thumbnail_poll()

    def _build_header(self):
        header = ttk.Frame(self, style="NavigatorHeader.TFrame", padding=(10, 10, 8, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="NAVIGATOR",
            style="NavigatorTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            textvariable=self.count_var,
            style="NavigatorCount.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def set_jobs(self, jobs, selected_index=-1):
        self._jobs = tuple(jobs)
        self._job_by_id = {job.id: job for job in self._jobs}
        self._selected_index = selected_index
        self._prune_caches()

        total = len(self._jobs)
        count_label = "page" if total == 1 else "pages"
        self.count_var.set(f"{total} {count_label}")
        self.canvas.configure(scrollregion=(0, 0, self.CARD_WIDTH, self._content_height()))
        self._draw_scrollbar()
        self._schedule_render()

    def shutdown(self):
        for after_id in (self._render_after_id, self._thumbnail_poll_after_id):
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except (tk.TclError, ValueError):
                    pass
        self._render_after_id = None
        self._thumbnail_poll_after_id = None
        self._thumbnail_executor.shutdown(wait=False, cancel_futures=True)

    def _schedule_render(self, event=None):
        if self._render_after_id is not None:
            return
        self._render_after_id = self.after_idle(self._render_visible)

    def _render_visible(self):
        self._render_after_id = None
        self.canvas.delete("navigator")
        self._draw_scrollbar()

        if not self._jobs:
            self._draw_empty_state()
            return

        first, last = self._visible_range()
        for index in range(first, last):
            self._draw_card(index, self._jobs[index])

    def _draw_empty_state(self):
        width = max(self.CARD_WIDTH, self.canvas.winfo_width())
        self.canvas.create_text(
            width // 2,
            40,
            text="Open files to build a page list",
            fill="#a4a4a4",
            font=("Segoe UI", 9),
            width=150,
            justify=tk.CENTER,
            tags=("navigator",),
        )

    def _draw_card(self, index, job):
        y = self.CARD_GAP + index * (self.CARD_HEIGHT + self.CARD_GAP)
        x = 8
        selected = index == self._selected_index
        background = "#4a0718" if selected else "#181818"
        outline = "#e12a5b" if selected else "#242424"
        status = self._status_text(job)
        status_color = self._status_color(job)
        image = self._photo_for(job)

        self.canvas.create_rectangle(
            x,
            y,
            x + self.CARD_WIDTH,
            y + self.CARD_HEIGHT,
            fill=background,
            outline=outline,
            width=1 if selected else 0,
            tags=("navigator", f"job:{job.id}", f"index:{index}"),
        )
        self.canvas.create_text(
            x + 10,
            y + 16,
            text=f"#{index + 1}",
            anchor=tk.W,
            fill=status_color,
            font=("Segoe UI Semibold", 8),
            tags=("navigator", f"job:{job.id}", f"index:{index}"),
        )
        self.canvas.create_image(
            x + self.CARD_WIDTH // 2,
            y + 102,
            image=image,
            anchor=tk.CENTER,
            tags=("navigator", f"job:{job.id}", f"index:{index}"),
        )
        self.canvas.create_text(
            x + self.CARD_WIDTH // 2,
            y + 190,
            text=str(index + 1),
            fill="#ffffff",
            font=("Segoe UI Semibold", 10),
            tags=("navigator", f"job:{job.id}", f"index:{index}"),
        )
        self.canvas.create_text(
            x + self.CARD_WIDTH // 2,
            y + 211,
            text=status,
            fill="#a4a4a4",
            font=("Segoe UI", 8),
            tags=("navigator", f"job:{job.id}", f"index:{index}"),
        )

    def _photo_for(self, job):
        cache_key = self._thumbnail_cache_key(job)
        cached = self._photo_cache.get(cache_key)
        if cached is not None:
            return cached

        pil_image = self._pil_cache.pop(cache_key, None)
        if pil_image is not None:
            photo = ImageTk.PhotoImage(pil_image)
            self._photo_cache[cache_key] = photo
            return photo

        self._request_thumbnail(job, cache_key)
        return self._placeholder_thumbnail()

    def _request_thumbnail(self, job, cache_key):
        if cache_key in self._pending_thumbnails:
            return
        self._pending_thumbnails.add(cache_key)
        self._thumbnail_executor.submit(
            self._load_thumbnail_worker,
            job.id,
            job.input_path,
            cache_key,
            self.THUMBNAIL_SIZE,
            self._thumbnail_results,
        )

    @staticmethod
    def _load_thumbnail_worker(job_id, input_path, cache_key, thumbnail_size, results):
        try:
            with Image.open(input_path) as image:
                source = image.convert("RGB")
                resampling = getattr(Image, "Resampling", Image)
                source.thumbnail(thumbnail_size, resampling.LANCZOS)
                canvas = Image.new("RGB", thumbnail_size, "#0f0f0f")
                left = (thumbnail_size[0] - source.width) // 2
                top = (thumbnail_size[1] - source.height) // 2
                canvas.paste(source, (left, top))
        except (OSError, ValueError):
            canvas = Image.new("RGB", thumbnail_size, "#202020")

        results.put(ThumbnailResult(job_id=job_id, cache_key=cache_key, image=canvas))

    def _schedule_thumbnail_poll(self):
        if self._thumbnail_poll_after_id is not None:
            return
        self._thumbnail_poll_after_id = self.after(30, self._poll_thumbnail_results)

    def _poll_thumbnail_results(self):
        self._thumbnail_poll_after_id = None
        updated = False

        for _ in range(12):
            try:
                result = self._thumbnail_results.get_nowait()
            except queue.Empty:
                break

            self._pending_thumbnails.discard(result.cache_key)
            if result.job_id not in self._job_by_id:
                continue
            if self._thumbnail_cache_key(self._job_by_id[result.job_id]) != result.cache_key:
                continue
            self._pil_cache[result.cache_key] = result.image
            updated = True

        if updated:
            self._schedule_render()
        self._schedule_thumbnail_poll()

    def _placeholder_thumbnail(self):
        if self._placeholder is None:
            image = Image.new("RGB", self.THUMBNAIL_SIZE, "#202020")
            self._placeholder = ImageTk.PhotoImage(image)
        return self._placeholder

    def _visible_range(self):
        total = len(self._jobs)
        if total == 0:
            return 0, 0

        top = self.canvas.canvasy(0)
        bottom = self.canvas.canvasy(max(1, self.canvas.winfo_height()))
        stride = self.CARD_HEIGHT + self.CARD_GAP
        first = max(0, int(top // stride) - self.VIEWPORT_BUFFER)
        last = min(total, int(bottom // stride) + self.VIEWPORT_BUFFER + 2)
        return first, last

    def _content_height(self):
        if not self._jobs:
            return max(1, self.canvas.winfo_height())
        return self.CARD_GAP + len(self._jobs) * (self.CARD_HEIGHT + self.CARD_GAP)

    def _on_canvas_scroll(self, first, last):
        self._draw_scrollbar(float(first), float(last))

    def _on_scrollbar_click(self, event):
        self._scrollbar_moveto(event.y)

    def _on_scrollbar_drag(self, event):
        self._scrollbar_moveto(event.y)

    def _scrollbar_moveto(self, y):
        height = max(1, self.scrollbar.winfo_height())
        thumb_top, thumb_bottom = self._scrollbar_thumb_bounds()
        thumb_height = max(1, thumb_bottom - thumb_top)
        first, last = self.canvas.yview()
        visible_fraction = max(0.0, min(1.0, last - first))
        max_first = max(0.0, 1.0 - visible_fraction)
        track_position = (y - (thumb_height / 2)) / max(1, height - thumb_height)
        target = max_first * max(0.0, min(1.0, track_position))
        self.canvas.yview_moveto(max(0.0, min(max_first, target)))
        self._schedule_render()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._schedule_render()

    def _on_click(self, event):
        index = self._index_at_y(self.canvas.canvasy(event.y))
        if 0 <= index < len(self._jobs):
            self.on_select(index)

    def _index_at_y(self, y):
        stride = self.CARD_HEIGHT + self.CARD_GAP
        raw = int((y - self.CARD_GAP) // stride)
        card_top = self.CARD_GAP + raw * stride
        if y < card_top or y > card_top + self.CARD_HEIGHT:
            return -1
        return raw

    def _prune_caches(self):
        live_keys = {self._thumbnail_cache_key(job) for job in self._jobs}
        self._photo_cache = {
            key: image for key, image in self._photo_cache.items() if key in live_keys
        }
        self._pil_cache = {
            key: image for key, image in self._pil_cache.items() if key in live_keys
        }
        self._pending_thumbnails = {
            key for key in self._pending_thumbnails if key in live_keys
        }

    def _draw_scrollbar(self, first=None, last=None):
        if first is None or last is None:
            first, last = self.canvas.yview()

        self.scrollbar.delete("all")
        width = max(1, self.scrollbar.winfo_width())
        height = max(1, self.scrollbar.winfo_height())

        if first <= 0.0 and last >= 1.0:
            self.scrollbar.configure(background="#121212")
            return

        track_left = max(1, (width - 6) // 2)
        track_right = min(width - 1, track_left + 6)
        self.scrollbar.create_rectangle(
            track_left,
            0,
            track_right,
            height,
            fill="#181818",
            outline="#2a2a2a",
        )

        thumb_top, thumb_bottom = self._scrollbar_thumb_bounds(first, last)
        self.scrollbar.create_rectangle(
            track_left + 1,
            thumb_top,
            track_right - 1,
            thumb_bottom,
            fill="#4f5358",
            outline="#4f5358",
        )
        self.scrollbar.create_rectangle(
            track_left + 2,
            thumb_top + 1,
            track_right - 2,
            thumb_bottom - 1,
            fill="#70757b",
            outline="#70757b",
        )

    def _scrollbar_thumb_bounds(self, first=None, last=None):
        if first is None or last is None:
            first, last = self.canvas.yview()

        height = max(1, self.scrollbar.winfo_height())
        visible_fraction = max(0.0, min(1.0, last - first))
        thumb_height = max(36, int(height * visible_fraction))
        max_top = max(0, height - thumb_height)
        max_first = max(0.0, 1.0 - visible_fraction)

        if max_first <= 0.0 or first <= 0.0:
            thumb_top = 0
        elif last >= 1.0:
            thumb_top = max_top
        else:
            thumb_top = int(max_top * max(0.0, min(1.0, first / max_first)))
        return thumb_top, min(height, thumb_top + thumb_height)

    @staticmethod
    def _thumbnail_cache_key(job):
        try:
            stat = os.stat(job.input_path)
        except OSError:
            return (job.input_path, None, None)
        return (job.input_path, stat.st_mtime_ns, stat.st_size)

    @staticmethod
    def _status_text(job):
        if job.status == JobStatus.FAILED:
            return "failed"
        if job.detection_status == DetectionStatus.FAILED:
            return "detection failed"
        if job.detection_status == DetectionStatus.PENDING:
            return "queued"
        if job.detection_status == DetectionStatus.RUNNING:
            return "detecting"
        if job.status == JobStatus.RUNNING:
            return "translating"
        if job.status == JobStatus.SUCCEEDED:
            return "done"
        return f"{len(job.boxes)} bubble(s)"

    @staticmethod
    def _status_color(job):
        if (
            job.status == JobStatus.FAILED
            or job.detection_status == DetectionStatus.FAILED
        ):
            return "#ff6b72"
        if job.status == JobStatus.SUCCEEDED:
            return "#8bd184"
        if (
            job.status == JobStatus.RUNNING
            or job.detection_status == DetectionStatus.RUNNING
        ):
            return "#f2c66d"
        return "#7aa7ff"
