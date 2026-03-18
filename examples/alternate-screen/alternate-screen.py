"""alternate-screen example for ink-python."""

import random
import threading
import time

from ink_python import render, Box, Text, useApp, useInput
from ink_python.hooks import useEffect, useRef, useState


HEAD = "[]"
BODY = "##"
FOOD = "<>"
EMPTY = "  "
TICK_MS = 0.15
BOARD_WIDTH = 20
BOARD_HEIGHT = 15
BORDER_H = "\u2500" * (BOARD_WIDTH * 2)
BORDER_TOP = f"\u250c{BORDER_H}\u2510"
BORDER_BOTTOM = f"\u2514{BORDER_H}\u2518"

OFFSETS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

OPPOSITES = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}


def random_position(exclude):
    while True:
        point = {
            "x": random.randrange(BOARD_WIDTH),
            "y": random.randrange(BOARD_HEIGHT),
        }
        if not any(segment["x"] == point["x"] and segment["y"] == point["y"] for segment in exclude):
            return point


def initial_state():
    snake = [
        {"x": 10, "y": 7},
        {"x": 9, "y": 7},
        {"x": 8, "y": 7},
    ]
    return {
        "snake": snake,
        "food": random_position(snake),
        "score": 0,
        "game_over": False,
        "won": False,
    }


def tick_state(state, direction):
    if state["game_over"]:
        return state

    head = state["snake"][0]
    offset_x, offset_y = OFFSETS[direction]
    new_head = {"x": head["x"] + offset_x, "y": head["y"] + offset_y}

    if (
        new_head["x"] < 0
        or new_head["x"] >= BOARD_WIDTH
        or new_head["y"] < 0
        or new_head["y"] >= BOARD_HEIGHT
    ):
        return {**state, "game_over": True, "won": False}

    ate_food = new_head["x"] == state["food"]["x"] and new_head["y"] == state["food"]["y"]
    collision_segments = state["snake"] if ate_food else state["snake"][:-1]
    if any(segment["x"] == new_head["x"] and segment["y"] == new_head["y"] for segment in collision_segments):
        return {**state, "game_over": True, "won": False}

    new_snake = [new_head, *state["snake"]]
    if not ate_food:
        new_snake.pop()

    if ate_food and len(new_snake) == BOARD_WIDTH * BOARD_HEIGHT:
        return {
            "snake": new_snake,
            "food": state["food"],
            "score": state["score"] + 1,
            "game_over": True,
            "won": True,
        }

    return {
        "snake": new_snake,
        "food": random_position(new_snake) if ate_food else state["food"],
        "score": state["score"] + (1 if ate_food else 0),
        "game_over": False,
        "won": False,
    }


def build_board(snake, food):
    head_key = f"{snake[0]['x']},{snake[0]['y']}"
    snake_keys = {f"{segment['x']},{segment['y']}" for segment in snake}

    rows = [BORDER_TOP]
    for y in range(BOARD_HEIGHT):
        row = "\u2502"
        for x in range(BOARD_WIDTH):
            key = f"{x},{y}"
            if key == head_key:
                row += HEAD
            elif key in snake_keys:
                row += BODY
            elif food["x"] == x and food["y"] == y:
                row += FOOD
            else:
                row += EMPTY
        row += "\u2502"
        rows.append(row)

    rows.append(BORDER_BOTTOM)
    return "\n".join(rows)


def alternate_screen_example():
    app = useApp()
    game, set_game = useState(initial_state())
    direction = useRef("right")

    def setup():
        running = True

        def run():
            while running:
                time.sleep(TICK_MS)
                set_game(lambda state: tick_state(state, direction.current))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup, ())

    def on_input(char, key):
        if char == "q":
            app.exit()
            return

        if game["game_over"] and char == "r":
            direction.current = "right"
            set_game(initial_state())
            return

        current = direction.current
        if key.up_arrow and current != OPPOSITES["up"]:
            direction.current = "up"
        elif key.down_arrow and current != OPPOSITES["down"]:
            direction.current = "down"
        elif key.left_arrow and current != OPPOSITES["left"]:
            direction.current = "left"
        elif key.right_arrow and current != OPPOSITES["right"]:
            direction.current = "right"

    useInput(on_input)

    status = (
        "You won! Press r to restart or q to quit."
        if game["won"]
        else "Game over. Press r to restart or q to quit."
        if game["game_over"]
        else "Use arrow keys to move. Press q to quit."
    )

    return Box(
        Text("Snake", bold=True, color="cyan"),
        Text(f"Score: {game['score']}"),
        Text(build_board(game["snake"], game["food"])),
        Text(status, dimColor=not game["game_over"]),
        flexDirection="column",
        padding=1,
    )


if __name__ == "__main__":
    render(alternate_screen_example, alternate_screen=True).wait_until_exit()
