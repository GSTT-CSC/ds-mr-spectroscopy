from tests import DebuggingServerThread

s = DebuggingServerThread()
s.daemon = True


def pytest_configure(config):
    s.start()


def pytest_unconfigure(config):
    s.stop()