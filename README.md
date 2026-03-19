# ink-python

> React-like terminal UI library for Python - a port of [Ink](https://github.com/vadimdemedes/ink)

**ink-python** is a Python library for building interactive command-line applications. It provides a React-like component system for rendering terminal UIs using Flexbox layouts via Yoga.

## Features

- 🎨 **React-like Components** - Build CLI apps using familiar component patterns
- 📐 **Flexbox Layouts** - Use CSS Flexbox for terminal layouts via Yoga
- 🎯 **Type-safe** - Full type hints for better development experience
- ⌨️ **Input Handling** - Built-in keyboard input support
- 🖥️ **ANSI Styling** - Colors, bold, italic, and more
- 📦 **Zero-config** - Works out of the box

## Installation

```bash
pip install ink-python
```

## Quick Start

```python
from ink_python import render, Box, Text

def Counter():
    return Box(
        Text("Hello, World!", color="green", bold=True),
        flexDirection="column",
        alignItems="center"
    )

# Render the app
app = render(Counter)
app.wait_until_exit()
```

## Components

### Box

The `<Box>` component is an essential building block for layouts. It's like `<div style="display: flex">` in the browser.

```python
from ink_python import Box, Text

Box(
    Text("Left"),
    Text("Center"),
    Text("Right"),
    flexDirection="row",
    justifyContent="space-between",
    width=60
)
```

### Text

The `<Text>` component displays text with optional styling.

```python
from ink_python import Text

Text(
    "Hello, World!",
    color="green",
    backgroundColor="black",
    bold=True,
    italic=True,
    underline=True
)
```

## Hooks

### useInput

Handle keyboard input:

```python
from ink_python import useInput, Text

def InputDemo():
    def handle_input(input_char, key):
        if key.up_arrow:
            # Handle up arrow
            pass
        elif input_char == 'q':
            # Quit on 'q'
            pass

    useInput(handle_input)
    return Text("Press arrow keys or 'q' to quit")
```

### useApp

Access the app instance:

```python
from ink_python import useApp, Text

def AppDemo():
    app = useApp()

    def exit_app():
        app.exit()

    return Text("App is running")
```

### useWindowSize

Get terminal dimensions:

```python
from ink_python import useWindowSize, Text

def SizeDemo():
    width, height = useWindowSize()
    return Text(f"Terminal: {width}x{height}")
```

### useStdout / useStderr / useStdin

Access standard streams:

```python
from ink_python import useStdout, useStderr, useStdin, Text

def StreamDemo():
    stdout = useStdout()
    stderr = useStderr()
    stdin = useStdin()

    # Write directly to streams
    stderr.write("Debug message\n")
    return Text("Check stderr for debug output")
```

### useCursor

Control cursor visibility:

```python
from ink_python import useCursor, Text

def CursorDemo():
    # Hide cursor
    useCursor(False)
    return Text("Cursor is hidden")
```

### useFocus

Create focusable elements for keyboard navigation:

```python
from ink_python import useFocus, Text

def FocusDemo():
    is_focused, focus = useFocus(id="my-element")
    return Text(
        f"Item {'(focused)' if is_focused else ''}",
        color="green" if is_focused else "white"
    )
```

### useFocusManager

Programmatic focus control:

```python
from ink_python import useFocusManager, useFocus, Text

def FocusManagerDemo():
    focus_mgr = useFocusManager()

    def on_input(input_char, key):
        if input_char == '\t':  # Tab
            if key.get('shift'):
                focus_mgr.focus_previous()
            else:
                focus_mgr.focus_next()

    useInput(on_input)
    return Text("Press Tab to navigate focus")
```

### usePaste

Handle bracketed paste mode:

```python
from ink_python import usePaste, Text

def PasteDemo():
    def on_paste(data: str):
        # Handle pasted text
        pass

    usePaste(on_paste)
    return Text("Paste text here")
```

### useBoxMetrics

Get element dimensions and position:

```python
from ink_python import useBoxMetrics, Text

def MetricsDemo():
    ref, metrics = useBoxMetrics()
    # metrics.width, metrics.height, metrics.left, metrics.top
    return Box(
        ref=ref,
        child=Text(f"Size: {metrics.width}x{metrics.height}")
    )
```

### useIsScreenReaderEnabled

Check if screen reader is enabled:

```python
from ink_python import useIsScreenReaderEnabled, Text

def AccessibilityDemo():
    is_sr_enabled = useIsScreenReaderEnabled()
    return Text(
        f"Screen reader: {'enabled' if is_sr_enabled else 'disabled'}"
    )
```

### measureElement

Measure DOM element dimensions:

```python
from ink_python import measureElement, Box, Text

def MeasureDemo(node_ref):
    dims = measureElement(node_ref.current)
    return Text(f"Measured: {dims.width}x{dims.height}")
```

### renderToString

Render components to string (for non-interactive output):

```python
from ink_python import renderToString, Box, Text

output = renderToString(
    Box(
        Text("Hello"),
        Text("World"),
        flexDirection="column"
    ),
    columns=40,
    rows=10
)
print(output)
```

**Note:** `renderToString` requires explicit `columns` and `rows` parameters due to Yoga layout engine constraints. The output height is not auto-calculated from content.

```python
from ink_python import useInput, Text

def InputDemo():
    def handle_input(input_char, key):
        if key.up_arrow:
            # Handle up arrow
            pass
        elif input_char == 'q':
            # Quit on 'q'
            pass

    useInput(handle_input)
    return Text("Press arrow keys or 'q' to quit")
```

### useApp

Access the app instance:

```python
from ink_python import useApp, Text

def AppDemo():
    app = useApp()

    def exit_app():
        app.exit()

    return Text("App is running")
```

### useWindowSize

Get terminal dimensions:

```python
from ink_python import useWindowSize, Text

def SizeDemo():
    width, height = useWindowSize()
    return Text(f"Terminal: {width}x{height}")
```

## Styling

Box supports CSS Flexbox properties:

- `flexDirection`: `"row"` | `"column"` | `"row-reverse"` | `"column-reverse"`
- `justifyContent`: `"flex-start"` | `"center"` | `"flex-end"` | `"space-between"` | `"space-around"`
- `alignItems`: `"flex-start"` | `"center"` | `"flex-end"` | `"stretch"`
- `flexWrap`: `"nowrap"` | `"wrap"` | `"wrap-reverse"`
- `flexGrow`: number
- `flexShrink`: number
- `width`: number | str (e.g., `"50%"`)
- `height`: number | str
- `padding`: number
- `margin`: number
- `borderStyle`: `"single"` | `"double"` | `"round"` | `"bold"`
- And more...

## Examples

See the `examples/` directory for more examples:

- `examples/alternate-screen/` - Alternate-screen snake game
- `examples/borders/` - Border styles
- `examples/chat/` - Interactive chat UI
- `examples/static/` - Static output rendering
- `examples/terminal-resize/` - `useWindowSize` terminal resize demo
- `examples/use-focus/` - Keyboard focus navigation
- `examples/use-stderr/` - Ink-preserving stderr writes
- `examples/use-stdout/` - Ink-preserving stdout writes

## Dependencies

This library is a faithful Python port of the JavaScript [Ink](https://github.com/vadimdemedes/ink) library. Key dependencies:

- **[yoga](https://github.com/facebook/yoga)** - Flexbox layout engine
- **[wcwidth](https://github.com/jquast/wcwidth)** - Unicode character width
- **[colorama](https://github.com/tartley/colorama)** - ANSI color support

## License

MIT
