import time

import numpy as np
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

INPUT_MSG = 1
POSITIONS_MSG = 2
ID_MSG = 3


def get_input_datagram(actions_list):
    myPyDatagram = PyDatagram()
    myPyDatagram.addUint8(INPUT_MSG)
    if len(actions_list) != 2:
        print(f"The actions are not formatted properly")
        return myPyDatagram
    myPyDatagram.addFloat64(actions_list[0])
    myPyDatagram.addFloat64(actions_list[1])
    return myPyDatagram


class ClientInfoMin:
    def __init__(self, id_player) -> None:
        self.id = id_player
        self.position = None


class BaseClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

        self.cManager = QueuedConnectionManager()
        self.cReader = QueuedConnectionReader(self.cManager, 0)
        self.cWriter = ConnectionWriter(self.cManager, 0)
        self.connection = None
        
        self.id = None
        self.clients_min: list[ClientInfoMin] = []

        taskMgr.setupTaskChain("clientChain", numThreads=1, threadPriority=1)
        taskMgr.add(self.handle_disconnect, "dc_check", -42, taskChain="clientChain")
        taskMgr.add(self.poll, "poll", -38, taskChain="clientChain")

    def connect(self):
        self.connection = self.cManager.openTCPClientConnection(
            self.ip, self.port, 3000
        )
        if self.connection:
            self.cReader.addConnection(self.connection)
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

        if msg_ID == POSITIONS_MSG:
            self.handle_positions(my_iterator)
        if msg_ID == ID_MSG:
            player_ID = my_iterator.getUint8()
            self.id = player_ID
            
    def handle_positions(self, iterator):
        nb_clients = iterator.getUint8()
        clients_min_list = []
        for _ in range(nb_clients):
            c_id = iterator.getUint8()
            if c_id in [c.id for c in self.clients_min]:
                client_get = [obj for obj in self.clients_min if obj.id == c_id][0]
            else:
                client_get = ClientInfoMin(c_id)
            pos_x = iterator.getFloat64()
            pos_y = iterator.getFloat64()
            pos_player = np.array([pos_x, pos_y], dtype=float)
            client_get.position = pos_player
            clients_min_list.append(client_get)
        
        self.clients_min = clients_min_list
        return

    def send_input(self, input_action):
        if self.connection is None:
            return
        datagram = get_input_datagram(input_action)
        self.cWriter.send(datagram, self.connection)

    def handle_disconnect(self, task):
        if self.cManager.resetConnectionAvailable():
            connectionPointer = PointerToConnection()
            self.cManager.getResetConnection(connectionPointer)
            lostConnection = connectionPointer.p()

            print(f"Disconnected from server, exiting...")

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
        time.sleep(5)


if __name__ == "__main__":
    main()
