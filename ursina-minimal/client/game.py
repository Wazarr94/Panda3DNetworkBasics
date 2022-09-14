import time

import numpy as np
from client_object import BaseClient
from ursina import *

window.borderless = False
window.vsync = False
window.size = (800, 600)

app = Ursina(
    title="Square Game",
)
Client = BaseClient("localhost", 25565)
Client.connect()


class ClientInfoGame:
    def __init__(self, id_player) -> None:
        self.id = id_player
        self.position = None
        self.entity = None


clients_game: list[ClientInfoGame] = []
actions_player = np.array([0, 0], dtype=float)

current_time = 0
global_time = 0
last_update_time = 0
seconds_between_updates = 1 / 60


def action_handle():
    global actions_player, Client
    global global_time, last_update_time, seconds_between_updates

    actions_player = np.array([0, 0], dtype=float)
    global_time += time.dt

    actions_player[0] = held_keys["right arrow"] - held_keys["left arrow"]
    actions_player[1] = held_keys["up arrow"] - held_keys["down arrow"]

    if actions_player[0] != 0 or actions_player[1] != 0:
        if (global_time - last_update_time) >= seconds_between_updates:
            Client.send_input(actions_player)
            last_update_time = global_time


def add_new_entities(local_client_list, server_client_list):
    for client_up in server_client_list:
        local_client_list_id = [c.id for c in local_client_list]
        if not client_up.id in local_client_list_id:
            client_game = ClientInfoGame(client_up.id)
            client_game.entity = Entity(
                model="quad",
                color="#000000",
                scale=1,
                position=client_up.position,
            )
            local_client_list.append(client_game)
        else:
            client_game = [obj for obj in clients_game if obj.id == client_up.id][0]
            client_game.entity.position = client_up.position


def remove_expired_entities(local_client_list, server_client_list):
    for client_local in local_client_list:
        server_client_list_id = [c.id for c in server_client_list]
        if not client_local.id in server_client_list_id:
            destroy(client_local.entity)
            local_client_list = [
                obj for obj in local_client_list if obj.id != client_local.id
            ]


def update():
    if not Client.connection:
        return
    client_update_pos = Client.clients_min
    remove_expired_entities(clients_game, client_update_pos)
    add_new_entities(clients_game, client_update_pos)
    action_handle()


app.run()
