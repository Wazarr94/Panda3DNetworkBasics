import time

from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import (
    ConnectionWriter,
    NetAddress,
    NetDatagram,
    PointerToConnection,
    QueuedConnectionListener,
    QueuedConnectionManager,
    QueuedConnectionReader,
)

PRINT_MESSAGE = 1


class BaseServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

        self.cManager = QueuedConnectionManager()
        self.cListener = QueuedConnectionListener(self.cManager, 0)
        self.cReader = QueuedConnectionReader(self.cManager, 0)
        self.cWriter = ConnectionWriter(self.cManager, 0)

        self.socket = self.cManager.openTCPServerRendezvous(self.port, 10000)
        self.cListener.addConnection(self.socket)

        self.activeConnections = []

        taskMgr.setupTaskChain("serverChain", numThreads=1, threadPriority=1)
        taskMgr.add(self.listen, "listen", -39, taskChain="serverChain")
        taskMgr.add(self.poll, "poll", -40, taskChain="serverChain")

    def listen(self, task):
        if self.cListener.newConnectionAvailable():
            rendezvous = PointerToConnection()
            netAddress = NetAddress()
            newConnection = PointerToConnection()
            if self.cListener.getNewConnection(rendezvous, netAddress, newConnection):
                newConnection = newConnection.p()
                self.activeConnections.append(newConnection)
                self.cReader.addConnection(newConnection)

        return task.cont

    def poll(self, task):
        if self.cReader.dataAvailable():
            dgram = NetDatagram()
            if self.cReader.getData(dgram):
                self.parse(dgram)

        return task.cont

    def parse(self, dgram):
        my_iterator = PyDatagramIterator(dgram)
        msg_ID = my_iterator.getUint8()

        if msg_ID == PRINT_MESSAGE:
            str_recv = my_iterator.getString()
            print(f"> {str_recv}")

    def close(self):
        for aClient in self.activeConnections:
            self.cReader.removeConnection(aClient)
        self.activeConnections = []

        self.cManager.closeConnection(self.socket)
        self.socket = None


def main():
    server = BaseServer("localhost", 22501)

    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
