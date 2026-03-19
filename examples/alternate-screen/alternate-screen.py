"""Port of js_source/ink/examples/alternate-screen/alternate-screen.tsx."""

import random
import threading
import time

from pyinkcli import Box, Text, render, useApp, useInput, useWindowSize
from pyinkcli.hooks import useEffect, useRef, useState


HEAD = "🦄"
BODY = "✨"
FOOD = "🌈"
EMPTY = "  "
TICK_MS = 0.15
BOARD_WIDTH = 20
BOARD_HEIGHT = 15
BORDER_H = "─" * (BOARD_WIDTH * 2)
BORDER_TOP = f"┌{BORDER_H}┐"
BORDER_BOTTOM = f"└{BORDER_H}┘"
BOARD_WIDTH_CHARS = BOARD_WIDTH * 2 + 2
RAINBOW_COLORS = ["red", "#FF7F00", "yellow", "green", "cyan", "blue", "magenta"]

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

INITIAL_SNAKE = [
    {"x": 10, "y": 7},
    {"x": 9, "y": 7},
    {"x": 8, "y": 7},
]


def random_position(exclude):
    while True:
        point = {
            "x": random.randrange(BOARD_WIDTH),
            "y": random.randrange(BOARD_HEIGHT),
        }
        if not any(segment["x"] == point["x"] and segment["y"] == point["y"] for segment in exclude):
            return point


def initial_state():
    return {
        "snake": INITIAL_SNAKE,
        "food": random_position(INITIAL_SNAKE),
        "score": 0,
        "game_over": False,
        "won": False,
        "frame": 0,
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
            "frame": state["frame"] + 1,
        }

    return {
        "snake": new_snake,
        "food": random_position(new_snake) if ate_food else state["food"],
        "score": state["score"] + (1 if ate_food else 0),
        "game_over": False,
        "won": False,
        "frame": state["frame"] + 1,
    }


def build_board(snake, food):
    head_key = f"{snake[0]['x']},{snake[0]['y']}"
    snake_keys = {f"{segment['x']},{segment['y']}" for segment in snake}

    rows = [BORDER_TOP]
    for y in range(BOARD_HEIGHT):
        row = "│"
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
        row += "│"
        rows.append(row)

    rows.append(BORDER_BOTTOM)
    return "\n".join(rows)


def alternate_screen_example():
    app = useApp()
    columns, _ = useWindowSize()
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

        if game["game_over"]:
            return

        current = direction.current
        if key.up_arrow and current != "down":
            direction.current = "up"
        elif key.down_arrow and current != "up":
            direction.current = "down"
        elif key.left_arrow and current != "right":
            direction.current = "left"
        elif key.right_arrow and current != "left":
            direction.current = "right"

    useInput(on_input)

    title_color = RAINBOW_COLORS[game["frame"] % len(RAINBOW_COLORS)]
    board = build_board(game["snake"], game["food"])
    margin_left = max((columns - BOARD_WIDTH_CHARS) // 2, 0)

    if game["game_over"]:
        status = Box(
            Text("You Win! " if game["won"] else "Game Over! ", bold=True, color="red"),
            Text("r: restart | q: quit", dimColor=True),
            justifyContent="center",
            marginTop=1,
        )
    else:
        status = Box(
            Text("Arrow keys: move | Eat 🌈 to grow | q: quit", dimColor=True),
            justifyContent="center",
            marginTop=1,
        )

    return Box(
        Box(
            Text("🦄 Unicorn Snake 🦄", bold=True, color=title_color),
            justifyContent="center",
        ),
        Box(
            Text(f"Score: {game['score']}", bold=True, color="yellow"),
            justifyContent="center",
            marginTop=1,
        ),
        Box(
            Text(board),
            marginLeft=margin_left,
            marginTop=1,
        ),
        status,
        flexDirection="column",
        paddingY=1,
    )


def run_alternate_screen_example():
    return render(alternate_screen_example, alternate_screen=True)


if __name__ == "__main__":
    run_alternate_screen_example().wait_until_exit()
