"""PTY integration tests for patch_console and alternate-screen teardown."""

from __future__ import annotations

import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import textwrap
import time
from pathlib import Path


def _run_python_in_pty(
    source: str,
    *,
    send: bytes = b"",
    send_after_text: str | None = None,
    send_delay_after_text: float = 0.0,
    timeout: float = 3.0,
    rows: int | None = None,
    cols: int | None = None,
) -> str:
    master_fd, slave_fd = pty.openpty()
    if rows is not None or cols is not None:
        winsz = struct.pack("HHHH", rows or 24, cols or 80, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsz)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    existing_pythonpath = env.get("PYTHONPATH")
    project_src = str((Path(__file__).resolve().parents[1] / "src"))
    env["PYTHONPATH"] = (
        project_src if not existing_pythonpath else f"{project_src}{os.pathsep}{existing_pythonpath}"
    )

    process = subprocess.Popen(
        [sys.executable, "-c", source],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        env=env,
    )
    os.close(slave_fd)

    captured = bytearray()
    deadline = time.time() + timeout
    sent = False
    send_not_before: float | None = None

    try:
        while time.time() < deadline:
            if send and not sent and send_after_text is None:
                os.write(master_fd, send)
                sent = True

            if (
                send
                and not sent
                and send_not_before is not None
                and time.time() >= send_not_before
            ):
                os.write(master_fd, send)
                sent = True

            ready, _, _ = select.select([master_fd], [], [], 0.05)
            if master_fd in ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                captured.extend(chunk)
                if (
                    send
                    and not sent
                    and send_after_text is not None
                    and send_after_text.encode() in captured
                    and send_not_before is None
                ):
                    send_not_before = time.time() + send_delay_after_text

            if process.poll() is not None:
                while True:
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                break
    finally:
        process.kill()
        process.wait(timeout=1)
        os.close(master_fd)

    return captured.decode("utf-8", errors="replace")


def test_patch_console_print_and_stderr_are_routed_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        import sys
        from pyinkcli import Text, render

        app = render(Text("frame"), patch_console=True, interactive=True)
        print("hello from print")
        sys.stderr.write("problem on stderr\\n")
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert "hello from print" in output
    assert "problem on stderr" in output
    assert "frame" in output


def test_ctrl_c_exits_interactive_app_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render

        app = render(Text("frame"), patch_console=False, interactive=True)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(source, send=b"\x03", timeout=3.0)

    assert "frame" in output


def test_interactive_frame_uses_synchronized_output_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render

        app = render(Text("frame"), patch_console=False, interactive=True)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    frame_index = output.find("frame")
    begin_index = output.find("\x1b[?2026h")
    end_index = output.find("\x1b[?2026l")
    assert frame_index != -1
    assert begin_index != -1
    assert end_index != -1
    assert begin_index < frame_index < end_index


def test_rerender_wraps_each_real_interactive_frame_in_synchronized_output() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render

        app = render(Text("one"), patch_console=False, interactive=True)
        app.rerender(Text("two"))
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    first_begin = output.find("\x1b[?2026h")
    first_end = output.find("\x1b[?2026l")
    second_begin = output.find("\x1b[?2026h", first_end + 1)
    second_end = output.find("\x1b[?2026l", first_end + 1)
    assert first_begin < output.find("one") < first_end
    assert second_begin < output.find("two") < second_end


def test_cursor_only_update_uses_synchronized_output_for_each_committed_frame() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render
        from pyinkcli.component import component
        from pyinkcli.hooks.use_cursor import useCursor

        POS = {"x": 0, "y": 0}

        @component
        def Example():
            cursor = useCursor()
            cursor.setCursorPosition(POS)
            return Text("same")

        app = render(Example, patch_console=False, interactive=True)
        POS = {"x": 1, "y": 0}
        app.rerender(Example)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    first_begin = output.find("\x1b[?2026h")
    first_end = output.find("\x1b[?2026l")
    second_begin = output.find("\x1b[?2026h", first_end + 1)
    second_end = output.find("\x1b[?2026l", first_end + 1)
    assert first_begin < output.find("same") < first_end
    assert second_begin < second_end


def test_overlay_restore_last_output_keeps_synchronized_output_boundaries() -> None:
    source = textwrap.dedent(
        """
        import sys
        from pyinkcli.ink import Ink, Options
        from pyinkcli import Text

        ink = Ink(
            Options(
                stdout=sys.stdout,
                stdin=sys.stdin,
                stderr=sys.stderr,
                patch_console=False,
                interactive=True,
            )
        )
        ink.render(Text("frame"))
        ink._write_to_stdout("overlay\\n")
        ink.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    second_begin = output.find("\x1b[?2026h", output.find("\x1b[?2026l") + 1)
    second_end = output.find("\x1b[?2026l", second_begin + 1)
    overlay_index = output.find("overlay")
    frame_index = output.rfind("frame")
    assert second_begin < overlay_index < frame_index < second_end


def test_incremental_rendering_wraps_each_real_update_in_synchronized_output() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render

        app = render(
            Text("one"),
            patch_console=False,
            interactive=True,
            incremental_rendering=True,
        )
        app.rerender(Text("two"))
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    first_begin = output.find("\x1b[?2026h")
    first_end = output.find("\x1b[?2026l")
    second_begin = output.find("\x1b[?2026h", first_end + 1)
    second_end = output.find("\x1b[?2026l", first_end + 1)
    assert first_begin < output.find("one") < first_end
    assert second_begin < output.find("two") < second_end


def test_fullscreen_to_normal_clear_path_keeps_synchronized_output_boundaries() -> None:
    lines = ", ".join([f'Text(\"L{i:02d}\")' for i in range(12)])
    source = textwrap.dedent(
        f"""
        from pyinkcli import Text, Box, render

        app = render(
            Box({lines}, flexDirection="column"),
            patch_console=False,
            interactive=True,
        )
        app.rerender(Text("short"))
        app.unmount()
        """
    )
    output = _run_python_in_pty(source, rows=10, cols=80)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    clear_index = output.find("\x1b[2J\x1b[3J\x1b[H")
    second_begin = output.find("\x1b[?2026h", output.find("\x1b[?2026l") + 1)
    second_end = output.find("\x1b[?2026l", second_begin + 1)
    assert clear_index != -1
    assert second_begin < clear_index < output.find("short") < second_end


def test_static_output_preserves_clear_static_main_frame_order() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, Box, Static, render
        from pyinkcli.component import component

        ITEMS = ["A"]
        LABEL = "frame-1"

        @component
        def Example():
            return Box(
                Static(items=ITEMS, renderItem=lambda item, index: Text(item)),
                Text(LABEL),
                flexDirection="column",
            )

        app = render(Example, patch_console=False, interactive=True)
        ITEMS = ["A", "B"]
        LABEL = "frame-2"
        app.rerender(Example)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    assert output.startswith("\x1b[?2026hA\r\n")
    second_begin = output.find("\x1b[?2026h", output.find("\x1b[?2026l") + 1)
    second_end = output.find("\x1b[?2026l", second_begin + 1)
    clear_index = output.find("\x1b[2K\x1b[1A\x1b[2K\x1b[G", second_begin)
    b_index = output.find("B\r\n", second_begin)
    frame_index = output.find("frame-2\r\n", second_begin)
    assert clear_index != -1
    assert second_begin < clear_index < b_index < frame_index < second_end


def test_incremental_rendering_with_static_matches_static_frame_boundaries() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, Box, Static, render
        from pyinkcli.component import component

        ITEMS = ["A"]
        LABEL = "frame-1"

        @component
        def Example():
            return Box(
                Static(items=ITEMS, renderItem=lambda item, index: Text(item)),
                Text(LABEL),
                flexDirection="column",
            )

        app = render(
            Example,
            patch_console=False,
            interactive=True,
            incremental_rendering=True,
        )
        ITEMS = ["A", "B"]
        LABEL = "frame-2"
        app.rerender(Example)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    assert output.startswith("\x1b[?2026hA\r\n")
    assert "B\r\nframe-2\r\n" in output


def test_patch_console_with_static_preserves_overlay_restore_order() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, Box, Static, render
        from pyinkcli.component import component

        ITEMS = ["A"]

        @component
        def Example():
            return Box(
                Static(items=ITEMS, renderItem=lambda item, index: Text(item)),
                Text("frame"),
                flexDirection="column",
            )

        app = render(Example, patch_console=True, interactive=True)
        print("overlay-line")
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    assert output.startswith("\x1b[?2026hA\r\n")
    second_begin = output.find("\x1b[?2026h", output.find("\x1b[?2026l") + 1)
    second_end = output.find("\x1b[?2026l", second_begin + 1)
    overlay_index = output.find("overlay-line\r\n", second_begin)
    frame_index = output.find("frame\r\n", overlay_index)
    assert second_begin < overlay_index < frame_index < second_end


def test_alternate_screen_with_static_matches_expected_raw_order() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, Box, Static, render
        from pyinkcli.component import component

        ITEMS = ["A"]

        @component
        def Example():
            return Box(
                Static(items=ITEMS, renderItem=lambda item, index: Text(item)),
                Text("frame"),
                flexDirection="column",
            )

        app = render(
            Example,
            patch_console=False,
            interactive=True,
            alternate_screen=True,
        )
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?1049h") == 1
    assert output.count("\x1b[?1049l") == 1
    assert output.count("\x1b[?2026h") == 1
    assert output.count("\x1b[?2026l") == 1
    assert output.startswith("\x1b[?1049h\x1b[?25l\x1b[?2026hA\r\n")
    assert "frame\r\n" in output


def test_resize_clear_then_rebuild_keeps_synchronized_output_boundaries() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text
        from pyinkcli.ink import Ink, Options
        import sys

        ink = Ink(
            Options(
                stdout=sys.stdout,
                stdin=sys.stdin,
                stderr=sys.stderr,
                patch_console=False,
                interactive=True,
            )
        )
        ink.render(Text("resize-frame"))
        ink._last_terminal_width = 80
        ink._get_viewport_rows = lambda is_tty: 24
        ink._handle_resize = lambda: (
            ink._reset_rendered_frame(),
            ink._on_render_callback(),
            setattr(ink, "_last_terminal_width", 40),
        )
        ink._handle_resize()
        ink.unmount()
        """
    )
    output = _run_python_in_pty(source)

    assert output.count("\x1b[?2026h") == 2
    assert output.count("\x1b[?2026l") == 2
    first_end = output.find("\x1b[?2026l")
    second_begin = output.find("\x1b[?2026h", first_end + 1)
    second_end = output.find("\x1b[?2026l", second_begin + 1)
    clear_index = output.find("\x1b[2K\x1b[1A\x1b[2K\x1b[G", first_end + 1)
    frame_index = output.find("resize-frame", first_end + 1)
    assert clear_index != -1
    assert first_end < clear_index < second_begin < frame_index < second_end


def test_alternate_screen_teardown_console_output_uses_native_stream_after_restore() -> None:
    source = textwrap.dedent(
        """
        import sys
        from pyinkcli import Text, render
        from pyinkcli.component import component
        from pyinkcli.hooks import useEffect

        @component
        def Example():
            def effect():
                def cleanup():
                    print("cleanup stdout")
                    sys.stderr.write("cleanup stderr\\n")
                return cleanup
            useEffect(effect, ())
            return Text("frame")

        app = render(Example, patch_console=True, interactive=True, alternate_screen=True)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    exit_index = output.rfind("\x1b[?1049l")
    assert exit_index != -1
    assert 0 <= output.find("cleanup stdout") < exit_index
    assert 0 <= output.find("cleanup stderr") < exit_index


def test_ctrl_c_with_patch_console_and_alternate_screen_runs_teardown_sequence() -> None:
    source = textwrap.dedent(
        """
        import sys
        from pyinkcli import Text, render
        from pyinkcli.component import component
        from pyinkcli.hooks import useEffect

        @component
        def Example():
            def effect():
                def cleanup():
                    print("cleanup stdout")
                    sys.stderr.write("cleanup stderr\\n")
                return cleanup
            useEffect(effect, ())
            return Text("frame")

        app = render(Example, patch_console=True, interactive=True, alternate_screen=True)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(
        source,
        send=b"\x03",
        send_after_text="frame",
        timeout=4.0,
    )

    exit_index = output.rfind("\x1b[?1049l")
    cleanup_stdout_index = output.find("cleanup stdout")
    cleanup_stderr_index = output.find("cleanup stderr")
    assert exit_index != -1
    assert cleanup_stdout_index != -1
    assert cleanup_stderr_index != -1
    assert cleanup_stdout_index < exit_index
    assert cleanup_stderr_index < exit_index


def test_q_exit_with_patch_console_and_alternate_screen_runs_teardown_sequence() -> None:
    source = textwrap.dedent(
        """
        import sys
        from pyinkcli import Text, render, useInput, useApp
        from pyinkcli.component import component
        from pyinkcli.hooks import useEffect

        @component
        def Example():
            app = useApp()

            def on_input(char, key):
                if char == "q":
                    app.exit()

            useInput(on_input)

            def effect():
                def cleanup():
                    print("cleanup stdout")
                    sys.stderr.write("cleanup stderr\\n")
                return cleanup
            useEffect(effect, ())
            return Text("frame")

        app = render(Example, patch_console=True, interactive=True, alternate_screen=True)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(
        source,
        send=b"q",
        send_after_text="frame",
        timeout=4.0,
    )

    exit_index = output.rfind("\x1b[?1049l")
    cleanup_stdout_index = output.find("cleanup stdout")
    cleanup_stderr_index = output.find("cleanup stderr")
    assert exit_index != -1
    assert cleanup_stdout_index != -1
    assert cleanup_stderr_index != -1
    assert cleanup_stdout_index < exit_index
    assert cleanup_stderr_index < exit_index


def test_utf8_input_is_not_mojibake_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render, useInput, useApp
        from pyinkcli.component import component
        from pyinkcli.hooks import useState

        @component
        def Example():
            app = useApp()
            value, set_value = useState("")

            def on_input(char, key):
                if key.return_pressed:
                    app.exit()
                    return
                if char:
                    set_value(lambda current: current + char)

            useInput(on_input)
            return Text(value or "ready")

        app = render(Example, patch_console=False, interactive=True)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(
        source,
        send="中文\r".encode(),
        send_after_text="ready",
        timeout=4.0,
    )

    assert "中文" in output
    assert "ä¸" not in output


def test_bracketed_paste_with_cjk_text_is_delivered_as_one_paste_event() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render, useApp
        from pyinkcli.component import component
        from pyinkcli.hooks import useState
        from pyinkcli.hooks.use_paste import usePaste

        @component
        def Example():
            app = useApp()
            value, set_value = useState("")

            def on_paste(text):
                set_value(text)
                app.exit()

            usePaste(on_paste)
            return Text(value or "ready")

        app = render(Example, patch_console=False, interactive=True)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(
        source,
        send=b"\x1b[200~hello\xe4\xb8\xad\xe6\x96\x87\nworld\x1b[201~",
        send_after_text="ready",
        send_delay_after_text=0.1,
        timeout=4.0,
    )

    assert "hello中文" in output
    assert "world" in output
    assert "ä¸" not in output


def test_alternate_screen_cursor_lifecycle_matches_js_ownership_boundaries() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render

        app = render(Text("frame"), patch_console=False, interactive=True, alternate_screen=True)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source)

    enter_index = output.find("\x1b[?1049h")
    exit_index = output.rfind("\x1b[?1049l")
    assert enter_index != -1
    assert exit_index != -1
    assert enter_index < output.find("frame") < exit_index
    assert output.count("\x1b[?25l") == 2
    assert output.count("\x1b[?25h") == 4


def test_incremental_rendering_example_preserves_selected_label_and_service_copy_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        import runpy
        from pathlib import Path

        runpy.run_path(
            str(Path("examples/incremental-rendering/index.py")),
            run_name="__main__",
        )
        """
    )
    output = _run_python_in_pty(
        source,
        send=b"q",
        send_after_text="incrementalRendering=true",
        send_delay_after_text=0.2,
        timeout=4.0,
        rows=40,
        cols=180,
    )

    assert "Incremental Rendering Demo - incrementalRendering=true" in output
    assert "System Services Monitor (17 of 30 services):" in output
    assert "Server Authentication Module" in output
    assert "Selected:" in output


def test_use_window_size_reads_real_pty_dimensions() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render, useWindowSize
        from pyinkcli.component import component

        @component
        def Example():
            columns, rows = useWindowSize()
            return Text(f"size={columns}x{rows}")

        app = render(Example, patch_console=False, interactive=True)
        app.unmount()
        """
    )
    output = _run_python_in_pty(source, rows=40, cols=180)

    assert "size=180x40" in output


def test_use_input_discrete_updates_bypass_normal_throttle_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render, useApp, useInput
        from pyinkcli.hooks import useEffect, useState

        def Example():
            app = useApp()
            value, set_value = useState("idle")

            def maybe_exit():
                if value == "pressed":
                    app.exit()
                return None

            useEffect(maybe_exit, (value,))

            def on_input(input_char, key):
                set_value("pressed")

            useInput(on_input)
            return Text(value)

        app = render(Example, patch_console=False, interactive=True, max_fps=1)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(
        source,
        send=b"x",
        send_after_text="idle",
        send_delay_after_text=0.05,
        timeout=2.0,
    )

    assert "idle" in output
    assert "pressed" in output


def test_use_paste_discrete_updates_bypass_normal_throttle_in_real_pty() -> None:
    source = textwrap.dedent(
        """
        from pyinkcli import Text, render, useApp, usePaste
        from pyinkcli.hooks import useEffect, useState

        def Example():
            app = useApp()
            value, set_value = useState("idle")

            def maybe_exit():
                if value == "hello":
                    app.exit()
                return None

            useEffect(maybe_exit, (value,))

            def on_paste(text):
                set_value(text)

            usePaste(on_paste)
            return Text(value)

        app = render(Example, patch_console=False, interactive=True, max_fps=1)
        app.wait_until_exit()
        """
    )
    output = _run_python_in_pty(
        source,
        send=b"\x1b[200~hello\x1b[201~",
        send_after_text="idle",
        send_delay_after_text=0.05,
        timeout=2.0,
    )

    assert "idle" in output
    assert "hello" in output
