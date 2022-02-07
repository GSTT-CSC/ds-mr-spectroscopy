import os
import smtpd
import threading
import asyncore
from time import sleep


TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


class DebuggingServer(smtpd.DebuggingServer):

    def __init__(self, addr, port):
        smtpd.DebuggingServer.__init__(self, localaddr=(addr, port), remoteaddr=None)


class DebuggingServerThread(threading.Thread):

    def __init__(self, addr='localhost', port=4000):
        threading.Thread.__init__(self, target=asyncore.loop, kwargs={'timeout': 1})
        self.server = DebuggingServer(addr, port)

    def stop(self):
        """Stop listening now to port 25"""
        # close the SMTPserver to ensure no channels connect to asyncore
        self.server.close()
        # sleep(1)
        # # now it is save to wait for the thread to finish, i.e. for asyncore.loop() to exit
        # self.join()
