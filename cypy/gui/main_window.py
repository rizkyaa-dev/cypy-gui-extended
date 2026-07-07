import os
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cypy.gui.models.job import DetectionStatus, JobQueue, JobStatus
from cypy.gui.services.app_controller import GuiAppController
from cypy.gui.widgets import (
    ComparisonWorkspace,
    FileNavigator,
    MainToolBar,
    PageStatusBar,
)
from cypy.gui.workers import DetectionExecutor, GuiEventType, ProcessingExecutor


class MainWindow(ttk.Frame):
    POLL_INTERVAL_MS = 50
    MAX_EVENTS_PER_POLL = 25

    def __init__(self, root, controller=None, max_workers=1):
        super().__init__(root, style="App.TFrame")
        self.root = root
        self.controller = controller or GuiAppController()
        self.jobs = JobQueue()
        self.current_index = -1
        self.event_queue = queue.Queue()
        self.executor = ProcessingExecutor(
            self.controller.job_runner,
            event_queue=self.event_queue,
            max_workers=max_workers,
        )
        self.detection_executor = DetectionExecutor(
            self.controller.detect_bubbles,
            event_queue=self.event_queue,
        )
        self.active_job_ids = set()
        self.detecting_job_ids = set()
        self.pending_detection_job_ids = set()
        self._poll_after_id = None
        self._navigator_refresh_after_id = None

        self.language_var = tk.StringVar(
            value=self.controller.default_target_language()
        )
        self.status_var = tk.StringVar(value="Ready")
        self.page_var = tk.StringVar(value="0 / 0")

        self._configure_window()
        self._build_layout()
        self._schedule_event_poll()

    def _configure_window(self):
        self.root.title("cypy-extended")
        self.root.geometry("1280x820")
        self.root.minsize(920, 620)
        self.root.configure(background="#161616")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.pack(fill=tk.BOTH, expand=True)

    def _build_layout(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.toolbar = MainToolBar(
            self,
            language_var=self.language_var,
            status_var=self.status_var,
            page_var=self.page_var,
            on_open_files=self.add_files,
            on_previous=self.show_previous_page,
            on_next=self.show_next_page,
            on_translate=self.translate_current_page,
        )
        self.toolbar.grid(row=0, column=0, sticky="ew")

        content = ttk.Frame(self, style="App.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(2, weight=1)

        self.navigator = FileNavigator(content, on_select=self.show_page)
        self.navigator.grid(row=0, column=0, sticky="ns")
        ttk.Separator(content, orient=tk.VERTICAL).grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.workspace = ComparisonWorkspace(content)
        self.workspace.grid(row=0, column=2, sticky="nsew")

        self.page_status = PageStatusBar(self, on_remove=self.remove_current_page)
        self.page_status.grid(row=2, column=0, sticky="ew")
        self._refresh_navigator()

    def add_files(self):
        extensions = self.controller.supported_image_extensions()
        patterns = " ".join(f"*{extension}" for extension in extensions)
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Open manga pages",
            filetypes=(("Images", patterns), ("All files", "*.*")),
        )
        self.add_paths(paths)

    def add_paths(self, paths):
        extensions = tuple(
            extension.lower()
            for extension in self.controller.supported_image_extensions()
        )
        image_paths = [
            str(path)
            for path in paths
            if os.path.isfile(path) and str(path).lower().endswith(extensions)
        ]
        added = self.jobs.add_paths(image_paths)
        if not added:
            return

        for job in added:
            self.pending_detection_job_ids.add(job.id)

        if self.current_index < 0:
            self.show_page(0)
        else:
            self._refresh_page_controls()
            self._refresh_navigator()
        self._schedule_detection(preferred_index=self.current_index)
        self.page_status.set_message(f"Added {len(added)} page(s)")

    def show_previous_page(self):
        self.show_page(self.current_index - 1)

    def show_next_page(self):
        self.show_page(self.current_index + 1)

    def show_page(self, index):
        if not len(self.jobs):
            self.current_index = -1
            self.workspace.clear()
            self.page_status.clear()
            self._refresh_page_controls()
            self._refresh_navigator()
            return

        self.current_index = max(0, min(int(index), len(self.jobs) - 1))
        job = self.current_job
        output_path = (
            job.output_path
            if job.output_path and os.path.exists(job.output_path)
            else None
        )
        self.workspace.show_page(
            job.input_path,
            output_path=output_path,
            translated_message=self._translated_message(job),
            boxes=job.boxes,
            text_mask=job.text_mask,
        )
        self.page_status.set_page(
            job,
            self.current_index,
            removable=(
                job.id not in self.active_job_ids
                and job.id not in self.detecting_job_ids
            ),
        )
        self.page_status.set_message(self._page_message(job))
        self._refresh_page_controls()
        self._refresh_navigator()
        self._schedule_detection(preferred_index=self.current_index)

    def translate_current_page(self):
        job = self.current_job
        if (
            job is None
            or job.id in self.active_job_ids
            or job.detection_status in (DetectionStatus.PENDING, DetectionStatus.RUNNING)
        ):
            return

        target_language = self.language_var.get().strip()
        if not target_language:
            messagebox.showwarning(
                "Target language required",
                "Enter a target language before translating.",
                parent=self.root,
            )
            return

        if job.status != JobStatus.PENDING:
            job = job.reset()
            self.jobs.update(job)
            self.show_page(self.current_index)

        try:
            context = self.controller.create_processing_context(
                target_language=target_language,
                detected_boxes=(
                    job.boxes
                    if job.detection_status == DetectionStatus.SUCCEEDED
                    else None
                ),
            )
        except Exception as exc:
            messagebox.showerror(
                "Unable to start translation",
                str(exc),
                parent=self.root,
            )
            self.page_status.set_message(str(exc))
            return

        self.active_job_ids.add(job.id)
        self.status_var.set("Processing")
        self.toolbar.set_processing(True)
        self.page_status.set_page(
            job,
            self.current_index,
            removable=False,
        )
        self.executor.submit(job, context)

    def remove_current_page(self):
        job = self.current_job
        if (
            job is None
            or job.id in self.active_job_ids
            or job.id in self.detecting_job_ids
        ):
            return

        removed = self.jobs.remove(job.id)
        self.pending_detection_job_ids.discard(removed.id)
        if len(self.jobs):
            self.show_page(min(self.current_index, len(self.jobs) - 1))
        else:
            self.show_page(-1)

    @property
    def current_job(self):
        if self.current_index < 0 or self.current_index >= len(self.jobs):
            return None
        return self.jobs[self.current_index]

    def close(self):
        background_work = self.active_job_ids or self.detecting_job_ids
        if background_work and not messagebox.askyesno(
            "Background work in progress",
            "Cancel queued work and close? Active tasks may finish before the process exits.",
            parent=self.root,
        ):
            return

        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._navigator_refresh_after_id is not None:
            self.after_cancel(self._navigator_refresh_after_id)
            self._navigator_refresh_after_id = None
        self.detection_executor.shutdown(wait=False)
        self.executor.shutdown(wait=False)
        self.navigator.shutdown()
        self.root.destroy()

    def _refresh_page_controls(self):
        total = len(self.jobs)
        has_page = self.current_job is not None
        self.page_var.set(
            f"{self.current_index + 1} / {total}" if has_page else "0 / 0"
        )
        self.toolbar.set_page_state(
            can_previous=has_page and self.current_index > 0,
            can_next=has_page and self.current_index < total - 1,
            can_translate=(
                has_page
                and not self.active_job_ids
                and self.current_job.detection_status
                not in (DetectionStatus.PENDING, DetectionStatus.RUNNING)
            ),
        )

    def _refresh_navigator(self):
        if self._navigator_refresh_after_id is not None:
            return
        self._navigator_refresh_after_id = self.after_idle(
            self._flush_navigator_refresh
        )

    def _flush_navigator_refresh(self):
        self._navigator_refresh_after_id = None
        self.navigator.set_jobs(self.jobs.jobs, selected_index=self.current_index)

    @staticmethod
    def _page_message(job):
        if job.detection_status == DetectionStatus.PENDING:
            return "Waiting for bubble detection..."
        if job.detection_status == DetectionStatus.RUNNING:
            return "Detecting speech bubbles..."
        if job.detection_status == DetectionStatus.FAILED:
            return job.detection_error or "Bubble detection failed"
        if job.status == JobStatus.RUNNING:
            return job.message or "Translating..."
        if job.boxes:
            return f"Found {len(job.boxes)} speech bubble(s)"
        return "No speech bubbles found"

    @staticmethod
    def _translated_message(job):
        if job.status == JobStatus.RUNNING:
            return "Translation in progress..."
        if job.status == JobStatus.FAILED:
            return job.message or "Translation failed"
        if job.status == JobStatus.SUCCEEDED:
            return "Translated output is unavailable"
        return "Not translated yet"

    def _schedule_event_poll(self):
        self._poll_after_id = self.after(self.POLL_INTERVAL_MS, self._poll_events)

    def _poll_events(self):
        self._poll_after_id = None
        processed = 0
        while processed < self.MAX_EVENTS_PER_POLL:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
            processed += 1

        delay = 1 if not self.event_queue.empty() else self.POLL_INTERVAL_MS
        self._poll_after_id = self.after(delay, self._poll_events)

    def _handle_event(self, event):
        if event.type == GuiEventType.DETECTION_STARTED:
            self._detection_started(event.job_id)
            return

        if event.type in (
            GuiEventType.DETECTION_FINISHED,
            GuiEventType.DETECTION_FAILED,
        ):
            self._detection_completed(event.payload)
            return

        if event.type == GuiEventType.LOG:
            if self.current_job and self.current_job.id == event.job_id:
                self.page_status.set_message(event.message or "")
            return

        if event.type == GuiEventType.JOB_STARTED:
            self.jobs.update(event.payload)
            if self.current_job and self.current_job.id == event.job_id:
                self.show_page(self.current_index)
            else:
                self._refresh_navigator()
            return

        if event.type in (GuiEventType.JOB_FINISHED, GuiEventType.JOB_FAILED):
            self._complete_job(event.payload)

    def _detection_started(self, job_id):
        try:
            job = self.jobs.get(job_id)
        except KeyError:
            return
        updated = job.with_detection(DetectionStatus.RUNNING)
        self.jobs.update(updated)
        if not self.active_job_ids:
            self.status_var.set("Detecting")
        if self.current_job and self.current_job.id == job_id:
            self.show_page(self.current_index)
        else:
            self._refresh_navigator()

    def _detection_completed(self, result):
        self.detecting_job_ids.discard(result.job_id)
        try:
            job = self.jobs.get(result.job_id)
        except KeyError:
            return

        if result.error:
            updated = job.with_detection(
                DetectionStatus.FAILED,
                boxes=(),
                error=result.error,
                text_mask=None,
            )
        else:
            updated = job.with_detection(
                DetectionStatus.SUCCEEDED,
                boxes=result.boxes,
                text_mask=result.text_mask,
            )
        self.jobs.update(updated)

        if self.current_job and self.current_job.id == result.job_id:
            self.show_page(self.current_index)
        else:
            self._refresh_navigator()
        if not self.detecting_job_ids and not self.active_job_ids:
            self.status_var.set("Ready")
        self._refresh_page_controls()
        self._schedule_detection(preferred_index=self.current_index)

    def _complete_job(self, result):
        self.jobs.update(result.job)
        self.active_job_ids.discard(result.job.id)

        if self.current_job and self.current_job.id == result.job.id:
            self.show_page(self.current_index)
            if result.error:
                self.page_status.set_message(result.error)
        else:
            self._refresh_navigator()

        if not self.active_job_ids:
            self.status_var.set("Detecting" if self.detecting_job_ids else "Ready")
            self.toolbar.set_processing(False)
        self._refresh_page_controls()

    def _schedule_detection(self, preferred_index=None):
        if self.detecting_job_ids or not self.pending_detection_job_ids:
            return

        job = self._next_detection_job(preferred_index)
        if job is None:
            return

        self.pending_detection_job_ids.discard(job.id)
        self.detecting_job_ids.add(job.id)
        self.detection_executor.submit(job)

    def _next_detection_job(self, preferred_index=None):
        if not len(self.jobs):
            return None

        jobs = self.jobs.jobs
        if preferred_index is None or preferred_index < 0:
            preferred_index = 0

        preferred_index = max(0, min(int(preferred_index), len(jobs) - 1))
        order = sorted(
            range(len(jobs)),
            key=lambda index: (abs(index - preferred_index), index),
        )

        for index in order:
            job = jobs[index]
            if job.id in self.pending_detection_job_ids:
                return job
        return None
