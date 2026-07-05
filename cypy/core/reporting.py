from abc import ABC


class Reporter(ABC):
    def info(self, message):
        raise NotImplementedError

    def warning(self, message):
        raise NotImplementedError

    def error(self, message):
        raise NotImplementedError


class ConsoleReporter(Reporter):
    def info(self, message):
        print(message)

    def warning(self, message):
        print(message)

    def error(self, message):
        print(message)


class NullReporter(Reporter):
    def info(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass


class MemoryReporter(Reporter):
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))


def ensure_reporter(reporter=None):
    return reporter or ConsoleReporter()
