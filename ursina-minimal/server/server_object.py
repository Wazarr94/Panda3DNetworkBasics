import time

import numpy as np
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

INPUT_MSG = 1
POSITIONS_MSG = 2
ID_MSG = 3

player_positions = [
    np.array([-2, 0], dtype=float),
    np.array([0, 0], dtype=float),
    np.array([2, 0], dtype=float),
]


class ClientInfo:
    def __init__(self, conn, id_player) -> None:
        self.conn = conn
        self.id = id_player
        self.input = np.array([0, 0], dtype=float)
        self.position = player_positions[self.id % 3]


def send_positions(clients_list: list[ClientInfo]):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(POSITIONS_MSG)
    myPyDatagram.addUint8(len(clients_list))
    for client in clients_list:
        myPyDatagram.addUint8(client.id)
        myPyDatagram.addFloat64(client.position[0])
        myPyDatagram.addFloat64(client.position[1])
    return myPyDatagram


def get_id_datagram(client):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(ID_MSG)
    myPyDatagram.addUint8(client.id)
    return myPyDatagram


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

        self.cuid = 0
        self.activeConnections = []
        self.clients: list[ClientInfo] = []

        self.last_update = time.time()

        taskMgr.setupTaskChain("serverChain", numThreads=2, threadPriority=1)
        taskMgr.add(self.listen, "listen", -39, taskChain="serverChain")
        taskMgr.add(self.poll, "poll", -40, taskChain="serverChain")
        taskMgr.add(self.update_game, "update_game", 0, taskChain="serverChain")
        taskMgr.add(self.handle_disconnect, "disconnects", -42, taskChain="serverChain")

        print(f"Server started at {ip} and port {port}")

    def listen(self, task):
        if self.cListener.newConnectionAvailable():
            rendezvous = PointerToConnection()
            netAddress = NetAddress()
            newConnection = PointerToConnection()
            if self.cListener.getNewConnection(rendezvous, netAddress, newConnection):
                newConnection = newConnection.p()
                self.activeConnections.append(newConnection)
                client_connection = ClientInfo(newConnection, self.cuid)
                self.clients.append(client_connection)
                self.cReader.addConnection(newConnection)
                self.cuid += 1
                datagram_id = get_id_datagram(client_connection)
                self.cWriter.send(datagram_id, client_connection.conn)

        return task.cont

    def poll(self, task):
        if self.cReader.dataAvailable():
            dgram = NetDatagram()
            if self.cReader.getData(dgram):
                self.handle_msg(dgram)

        return task.cont

    def handle_disconnect(self, task):
        if self.cManager.resetConnectionAvailable():
            connectionPointer = PointerToConnection()
            self.cManager.getResetConnection(connectionPointer)
            lostConnection = connectionPointer.p()

            client_info = get_client(self.clients, lostConnection)
            print(f"Player #{client_info.id} disconnected!")

            self.clients.remove(client_info)
            self.activeConnections.remove(client_info.conn)
            self.cReader.removeConnection(client_info.conn)

        return task.cont

    def update_game(self, task):
        # physics update
        for client in self.clients:
            client.position += client.input * 0.05
            client.input = np.array([0, 0], dtype=float)

        # send update of positions
        positions_datagram = send_positions(self.clients)
        for aClient in self.clients:
            self.cWriter.send(positions_datagram, aClient.conn)

        self.last_update = time.time()

        return task.cont

    def handle_msg(self, dgram):
        conn_msg = dgram.getConnection()
        info_msg = get_client(self.clients, conn_msg)
        my_iterator = PyDatagramIterator(dgram)
        msg_ID = my_iterator.getUint8()

        if msg_ID == INPUT_MSG:
            self.handle_input(my_iterator, info_msg)

    def handle_input(self, iterator, client_info: ClientInfo):
        actions_x = iterator.getFloat64()
        actions_y = iterator.getFloat64()
        actions_player = np.array([actions_x, actions_y], dtype=float)
        client_info.input = actions_player

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
