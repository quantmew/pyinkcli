# pyinkcli

<div align="center">
	<br>
	<img width="220" alt="pyinkcli" src="media/logo.png">
	<br>
	<br>
</div>

> A Python fork and translation project of [Ink](https://github.com/vadimdemedes/ink) for building terminal UIs with a React-like component model.

`pyinkcli` is a Python implementation inspired by and translated from Ink. The upstream JavaScript source used for reference is vendored in [`js_source/ink`](js_source/ink). This repository is a fork, not the official Node.js package, and the API is adapted for Python where needed.

<div align="center">
	<img src="media/demo.svg" width="640" alt="Ink demo">
</div>

## Install

```bash
pip install pyinkcli
```

## Quick Start

```python
from pyinkcli import Box, Text, render


def Counter():
    return Box(
        Text("Hello from pyinkcli", color="green", bold=True),
        flexDirection="column",
        alignItems="center",
    )


app = render(Counter)
app.wait_until_exit()
```

## What This Repo Is

- A Python fork of Ink focused on translating the terminal UI model into Python
- A repo that keeps the upstream JS implementation nearby for parity work and audits
- A place for Python-native examples and tests under `examples/` and `tests/`

## Examples

- `examples/alternate-screen/`
- `examples/chat/`
- `examples/counter/`
- `examples/terminal-resize/`
- `examples/use-focus/`
- `examples/use-input/`

## License

MIT. The repository includes the upstream Ink license text in [`LICENSE`](LICENSE).
