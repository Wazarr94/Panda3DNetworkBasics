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
GET_NAME = 2


def send_message(string_send):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(PRINT_MESSAGE)
    myPyDatagram.addString(string_send)
    return myPyDatagram


class ClientInfo:
    def __init__(self, conn) -> None:
        self.conn = conn
        self.name = None


def get_client(clients, conn) -> ClientInfo:
    client_info_obj = [obj for obj in clients if obj.conn == conn][0]
    return client_info_obj


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
        self.clients = []

        taskMgr.setupTaskChain("serverChain", numThreads=1, threadPriority=1)
        taskMgr.add(self.listen, "listen", -39, taskChain="serverChain")
        taskMgr.add(self.poll, "poll", -40, taskChain="serverChain")
        taskMgr.add(self.handle_disconnect, "disconnects", -41, taskChain="serverChain")

        print(f"Server started at {ip} and port {port}")

    def listen(self, task):
        if self.cListener.newConnectionAvailable():
            rendezvous = PointerToConnection()
            netAddress = NetAddress()
            newConnection = PointerToConnection()
            if self.cListener.getNewConnection(rendezvous, netAddress, newConnection):
                newConnection = newConnection.p()
                self.activeConnections.append(newConnection)
                self.clients.append(ClientInfo(newConnection))
                self.cReader.addConnection(newConnection)

        return task.cont

    def poll(self, task):
        if self.cReader.dataAvailable():
            dgram = NetDatagram()
            if self.cReader.getData(dgram):
                self.handle_msg(dgram)

        return task.cont

    def handle_msg(self, dgram):
        conn_msg = dgram.getConnection()
        info_msg = get_client(self.clients, conn_msg)
        my_iterator = PyDatagramIterator(dgram)
        msg_ID = my_iterator.getUint8()

        if msg_ID == PRINT_MESSAGE:
            self.handle_chat(my_iterator, info_msg)
        elif msg_ID == GET_NAME:
            self.handle_join(my_iterator, info_msg)

    def handle_chat(self, iterator, client_info):
        str_recv = iterator.getString()
        print(f"{client_info.name}: {str_recv}")

        dgram_broadcast = send_message(f"{client_info.name}: {str_recv}")
        for aClient in self.clients:
            if aClient.conn != client_info.conn:
                self.cWriter.send(dgram_broadcast, aClient.conn)

    def handle_join(self, iterator, client_info):
        name_recv = iterator.getString()
        client_info.name = name_recv
        print(f"{client_info.name} connected !")

        dgram_broadcast = send_message(f"{client_info.name} connected !")
        for aClient in self.clients:
            if aClient.conn != client_info.conn:
                self.cWriter.send(dgram_broadcast, aClient.conn)

    def handle_disconnect(self, task):
        if self.cManager.resetConnectionAvailable():
            connectionPointer = PointerToConnection()
            self.cManager.getResetConnection(connectionPointer)
            lostConnection = connectionPointer.p()

            client_info = get_client(self.clients, lostConnection)
            print(f"{client_info.name} disconnected!")

            self.clients.remove(client_info)
            self.activeConnections.remove(client_info.conn)
            self.cReader.removeConnection(client_info.conn)

            dgram_broadcast = send_message(f"{client_info.name} disconnected !")
            for aClient in self.clients:
                self.cWriter.send(dgram_broadcast, aClient.conn)

        return task.cont

    def close(self):
        for aClient in self.activeConnections:
            self.cReader.removeConnection(aClient)
        self.activeConnections = []

        self.cManager.closeConnection(self.socket)
        self.socket = None


def main():
    server = BaseServer("localhost", 25565)

    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
