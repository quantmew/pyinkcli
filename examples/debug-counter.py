#!/usr/bin/env python3
"""Debug counter to trace render flow."""

import threading
import time
import sys

from ink_python import render, Text
from ink_python.hooks import useState, useEffect

# Monkey-patch to add debug logging

def patched_on_render_callback(self):
    """Handle render callback from reconciler with debug."""
    print(f"DEBUG [_on_render_callback]: called, is_unmounted={self._is_unmounted}", file=sys.stderr)

    self._has_pending_throttled_render = False

    if self._is_unmounted:
        print("DEBUG [_on_render_callback]: returning early (unmounted)", file=sys.stderr)
        return

    # Calculate layout BEFORE rendering
    print("DEBUG [_on_render_callback]: calling _calculate_layout", file=sys.stderr)
    self._calculate_layout()

    start_time = time.time()
    from ink_python.renderer import render as render_dom
    result = render_dom(self._root_node, self._is_screen_reader_enabled)
    print(f"DEBUG [_on_render_callback]: render_dom returned, output={result.output!r}, static_output={result.static_output!r}, interactive={self._interactive}, debug={self._debug}", file=sys.stderr)

    if self._on_render:
        from ink_python.ink import RenderMetrics
        metrics = RenderMetrics(render_time=time.time() - start_time)
        self._on_render(metrics)

    has_static_output = result.static_output and result.static_output != "\n"

    if self._debug:
        if has_static_output:
            self._full_static_output += result.static_output
        self._last_output = result.output
        self._last_output_to_render = result.output
        self._last_output_height = result.output_height
        self._stdout.write(self._full_static_output + result.output)
        print("DEBUG [_on_render_callback]: wrote in debug mode", file=sys.stderr)
        return

    if not self._interactive:
        if has_static_output:
            self._stdout.write(result.static_output)
        self._last_output = result.output
        self._last_output_to_render = result.output + "\n"
        self._last_output_height = result.output_height
        # WRITE OUTPUT EVEN IN NON-INTERACTIVE MODE!
        if result.output:
            self._stdout.write(result.output + "\n")
        print("DEBUG [_on_render_callback]: returning (non-interactive)", file=sys.stderr)
        return

    if has_static_output:
        self._full_static_output += result.static_output

    print("DEBUG [_on_render_callback]: calling _render_interactive_frame", file=sys.stderr)
    self._render_interactive_frame(
        result.output,
        result.output_height,
        result.static_output if has_static_output else "",
    )

# Patch Ink
from ink_python.ink import Ink
Ink._on_render_callback = patched_on_render_callback

# Debug create_node in dom.py
from ink_python import dom
original_create_node = dom.create_node

def debug_create_node(node_name):
    result = original_create_node(node_name)
    print(f"DEBUG [create_node]: created {node_name}, yoga_node={result.yoga_node}, measure_func={result.yoga_node.measure_func if result.yoga_node else 'N/A'}", file=sys.stderr)
    return result

dom.create_node = debug_create_node

# Debug append_child_node
original_append_child = dom.append_child_node

def debug_append_child(parent, child):
    print(f"DEBUG [append_child_node]: parent={parent.node_name}, child={child.node_name}, parent.yoga_node={parent.yoga_node}, child.yoga_node={child.yoga_node}", file=sys.stderr)
    if parent.yoga_node and child.yoga_node:
        print(f"DEBUG [append_child_node]: before insert, parent.yoga_node.children={len(parent.yoga_node.children)}", file=sys.stderr)
    original_append_child(parent, child)
    if parent.yoga_node and child.yoga_node:
        print(f"DEBUG [append_child_node]: after insert, parent.yoga_node.children={len(parent.yoga_node.children)}", file=sys.stderr)
    elif parent.yoga_node:
        print(f"DEBUG [append_child_node]: child has no yoga_node, skipping yoga insert", file=sys.stderr)

dom.append_child_node = debug_append_child

# Debug reconciler
from ink_python import reconciler
original_create_dom_node = reconciler.Reconciler._create_dom_node

def debug_create_dom_node(self, vnode, parent):
    vnode_type = vnode.type if not isinstance(vnode, str) else 'string'
    vnode_children = vnode.children if hasattr(vnode, 'children') else 'N/A'
    print(f"DEBUG [_create_dom_node]: vnode.type={vnode_type}, vnode.children={vnode_children}, parent={parent.node_name}", file=sys.stderr)
    result = original_create_dom_node(self, vnode, parent)
    print(f"DEBUG [_create_dom_node]: result node_name={result.node_name if result else None}, yoga_node={result.yoga_node if result else None}", file=sys.stderr)
    if result and hasattr(result, 'child_nodes') and result.child_nodes:
        print(f"DEBUG [_create_dom_node]: result.child_nodes={[(c.node_name, c.node_value if hasattr(c, 'node_value') else None) for c in result.child_nodes]}", file=sys.stderr)
    return result

reconciler.Reconciler._create_dom_node = debug_create_dom_node

# Debug renderer
from ink_python import renderer

def debug_render(node, is_screen_reader_enabled=False):
    from ink_python.renderer import _render_normal, _render_screen_reader, RenderResult

    print(f"DEBUG [renderer.render]: called, node.yoga_node={node.yoga_node}", file=sys.stderr)

    if node.yoga_node is None:
        print("DEBUG [renderer.render]: returning empty (no yoga_node)", file=sys.stderr)
        return RenderResult(output="", output_height=0, static_output="")

    # Debug yoga tree structure
    def print_yoga_tree(yoga_node, indent=0):
        prefix = "  " * indent
        print(f"{prefix}YogaNode: children={len(yoga_node.children)}, measure_func={yoga_node.measure_func}, "
              f"computed_width={yoga_node.get_computed_width()}, computed_height={yoga_node.get_computed_height()}, "
              f"is_dirty={yoga_node.is_dirty}", file=sys.stderr)
        for child in yoga_node.children:
            print_yoga_tree(child, indent + 1)

    print("DEBUG [renderer.render]: Yoga tree structure:", file=sys.stderr)
    print_yoga_tree(node.yoga_node)

    if is_screen_reader_enabled:
        print("DEBUG [renderer.render]: screen reader mode", file=sys.stderr)
        return _render_screen_reader(node)

    result = _render_normal(node)
    print(f"DEBUG [renderer.render]: _render_normal returned output={result.output!r}, height={result.output_height}, static={result.static_output!r}", file=sys.stderr)

    # Debug yoga node computed values
    if node.yoga_node:
        print(f"DEBUG [renderer.render]: yoga_node computed width={node.yoga_node.get_computed_width()}, height={node.yoga_node.get_computed_height()}", file=sys.stderr)

    return result

renderer.render = debug_render

print("DEBUG: Starting counter debug...", file=sys.stderr)

def counter_debug():
    """Render an auto-incrementing counter with debug output."""
    counter, set_counter = useState(0)
    print(f"DEBUG: counter_debug() called, counter={counter}", file=sys.stderr)

    def setup_timer():
        running = True
        call_count = [0]

        def tick():
            while running:
                time.sleep(0.5)
                call_count[0] += 1
                print(f"DEBUG: tick #{call_count[0]}, about to set_counter", file=sys.stderr)
                set_counter(lambda value: value + 1)
                print(f"DEBUG: tick #{call_count[0]}, set_counter done", file=sys.stderr)

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()
        print("DEBUG: timer thread started", file=sys.stderr)

        def cleanup():
            nonlocal running
            running = False
            print("DEBUG: cleanup called", file=sys.stderr)

        return cleanup

    useEffect(setup_timer, ())
    result = Text(f"{counter} tests passed", color="green")
    print(f"DEBUG: counter_debug() returning {result}", file=sys.stderr)
    return result


if __name__ == "__main__":
    print("DEBUG: About to call render()", file=sys.stderr)
    app = render(counter_debug, debug=False)
    print("DEBUG: render() returned, about to wait_until_exit()", file=sys.stderr)
    app.wait_until_exit()
    print("DEBUG: Done!", file=sys.stderr)
