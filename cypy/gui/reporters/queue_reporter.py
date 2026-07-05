from cypy.core.reporting import Reporter
from cypy.gui.events import GuiEvent, GuiEventType


class QueueReporter(Reporter):
    """Forwards core messages to a thread-safe GUI event queue."""

    def __init__(self, event_queue, job_id=None):
        self.event_queue = event_queue
        self.job_id = job_id

    def info(self, message):
        self._publish("info", message)

    def warning(self, message):
        self._publish("warning", message)

    def error(self, message):
        self._publish("error", message)

    def _publish(self, level, message):
        text = str(message).rstrip()
        if not text:
            return
        self.event_queue.put(
            GuiEvent(
                GuiEventType.LOG,
                job_id=self.job_id,
                level=level,
                message=text,
            )
        )
