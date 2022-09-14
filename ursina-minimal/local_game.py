import time

import numpy as np
from ursina import *

window.borderless = False
window.vsync = False
window.size = (800, 600)

app = Ursina(
    title="Square Game",
)

position_player = np.array([0, 0], dtype=float)
actions_player = np.array([0, 0], dtype=float)
entity_player = Entity(
    model="quad",
    color="#000000",
    scale=1,
    position=position_player,
)

current_time = 0
global_time = 0
last_update_time = 0
seconds_between_updates = 1 / 60


def action_handle():
    global actions_player, position_player, Client
    global global_time, last_update_time, seconds_between_updates

    actions_player = np.array([0, 0], dtype=float)
    global_time += time.dt

    actions_player[0] = held_keys["right arrow"] - held_keys["left arrow"]
    actions_player[1] = held_keys["up arrow"] - held_keys["down arrow"]

    if actions_player[0] != 0 or actions_player[1] != 0:
        if (global_time - last_update_time) >= seconds_between_updates:
            position_player += actions_player * 0.05
            entity_player.position = position_player
            last_update_time = global_time


def update():
    action_handle()


app.run()
