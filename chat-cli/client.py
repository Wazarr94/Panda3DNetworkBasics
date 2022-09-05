import time

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import (
    ConnectionWriter,
    NetDatagram,
    PointerToConnection,
    QueuedConnectionManager,
    QueuedConnectionReader,
)

PRINT_MESSAGE = 1
GET_NAME = 2


def send_message(string_send):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(PRINT_MESSAGE)
    myPyDatagram.addString(string_send)
    return myPyDatagram


def send_name(name):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(GET_NAME)
    myPyDatagram.addString(name)
    return myPyDatagram


class BaseClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

        self.cManager = QueuedConnectionManager()
        self.cReader = QueuedConnectionReader(self.cManager, 0)
        self.cWriter = ConnectionWriter(self.cManager, 0)
        self.connection = None
        taskMgr.setupTaskChain("clientChain", numThreads=1, threadPriority=1)
        taskMgr.add(self.handle_disconnect, "dc_check", -42, taskChain="clientChain")
        taskMgr.add(self.poll, "poll", -38, taskChain="clientChain")

    def connect(self):
        self.connection = self.cManager.openTCPClientConnection(
            self.ip, self.port, 3000
        )
        if self.connection:
            self.cReader.addConnection(self.connection)
            name_client = input("What's your name?\n> ")
            datagram_name = send_name(name_client)
            self.cWriter.send(datagram_name, self.connection)
            return True
        return False

    def poll(self, task):
        if self.cReader.dataAvailable():
            dgram = NetDatagram()
            if self.cReader.getData(dgram):
                self.handle_msg(dgram)

        return task.cont

    def handle_msg(self, dgram):
        my_iterator = PyDatagramIterator(dgram)
        msg_ID = my_iterator.getUint8()
        str_recv = my_iterator.getString()

        if msg_ID == PRINT_MESSAGE:
            print(str_recv)

    def chat(self):
        str_send = input("")
        datagram = send_message(str_send)
        if self.connection is None:
            return
        self.cWriter.send(datagram, self.connection)

    def handle_disconnect(self, task):
        if self.cManager.resetConnectionAvailable():
            connectionPointer = PointerToConnection()
            self.cManager.getResetConnection(connectionPointer)
            lostConnection = connectionPointer.p()

            print(f"Disconnected from server, press Enter to exit...")

            self.cReader.removeConnection(lostConnection)
            self.cManager.closeConnection(lostConnection)
            self.connection = None

        return task.cont

    def close(self):
        self.cReader.removeConnection(self.connection)
        self.cManager.closeConnection(self.connection)


def main():
    client = BaseClient("localhost", 25565)
    if not client.connect():
        print("Failed to connect!")
        return

    while client.connection is not None:
        client.chat()


if __name__ == "__main__":
    main()
