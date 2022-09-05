import time

from direct.distributed.PyDatagram import PyDatagram
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import (
    ConnectionWriter,
    NetDatagram,
    QueuedConnectionManager,
    QueuedConnectionReader,
)

PRINT_MESSAGE = 1


def send_message(string_send):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(PRINT_MESSAGE)
    myPyDatagram.addString(string_send)
    return myPyDatagram


class BaseClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

        self.cManager = QueuedConnectionManager()
        self.cReader = QueuedConnectionReader(self.cManager, 0)
        self.cWriter = ConnectionWriter(self.cManager, 0)
        self.connection = None

    def connect(self):
        self.connection = self.cManager.openTCPClientConnection(
            self.ip, self.port, 3000
        )
        if self.connection:
            self.cReader.addConnection(self.connection)
            taskMgr.add(self.poll, "client-poll", -38)
            return True
        return False

    def poll(self, task):
        if self.cReader.dataAvailable():
            dgram = NetDatagram()
            if self.cReader.getData(dgram):
                print("received message!")

        return task.cont

    def chat(self):
        str_send = input("> ")
        datagram = send_message(str_send)
        self.cWriter.send(datagram, self.connection)

    def close(self):
        self.cReader.removeConnection(self.connection)
        self.cManager.closeConnection(self.connection)


def main():
    client = BaseClient("localhost", 22501)
    if not client.connect():
        print("Failed to connect!")
        return

    while True:
        client.chat()


if __name__ == "__main__":
    main()
