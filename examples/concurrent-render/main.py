"""
并发渲染示例 - 大型列表性能测试

这个示例测试并发渲染在渲染大型列表时的性能。
展示时间切片如何让出主线程，保持 UI 响应。

特性：
- 渲染 10000 个列表项
- 支持滚动浏览
- 按任意键可中断当前渲染
"""

from pyinkcli import Text, useState, useInput, useLayoutEffect, render


def ListItem(item, index):
    """单个列表项"""
    return f"[{index:05d}] {item} - 数据内容 {index * 1000}"


def LargeList():
    """大型列表组件"""
    # 生成 10000 个测试数据
    total_items = 10000
    all_items = [f"Python 并发渲染测试项 {i}" for i in range(total_items)]

    # 当前可见范围
    visible_start, set_visible_start = useState(0)
    visible_count = 30  # 可见区域能显示的项目数

    # 性能指标
    render_time_ms, set_render_time_ms = useState(0)
    is_rendering, set_is_rendering = useState(False)

    # 计算可见范围
    visible_end = min(visible_start + visible_count, total_items)
    visible_items = all_items[visible_start:visible_end]

    def handle_input(key, key_obj):
        if key == "q" or key == "Q":
            # 退出
            app.exit()
        elif key == "up" or key == "k":
            # 向上滚动
            if visible_start > 0:
                set_visible_start(max(0, visible_start - 10))
        elif key == "down" or key == "j":
            # 向下滚动
            set_visible_start(min(total_items - visible_count, visible_start + 10))
        elif key == "pageup":
            # 上一页
            set_visible_start(max(0, visible_start - visible_count))
        elif key == "pagedown":
            # 下一页
            set_visible_start(min(total_items - visible_count, visible_start + visible_count))
        elif key == "home":
            # 顶部
            set_visible_start(0)
        elif key == "end":
            # 底部
            set_visible_start(total_items - visible_count)

    useInput(handle_input)

    # 构建输出
    progress_pct = (visible_end / total_items) * 100

    lines = [
        f"{'=' * 70}",
        f"并发渲染大型列表示例 (按 'q' 退出)",
        f"{'=' * 70}",
        f"",
        f"总项目数：{total_items:,}",
        f"当前范围：{visible_start:,} - {visible_end:,} ({progress_pct:.1f}%)",
        f"渲染时间：{render_time_ms:.2f}ms {'(渲染中...)' if is_rendering else ''}",
        f"",
        f"{'-' * 70}",
    ]

    # 渲染可见项目
    for i, item in enumerate(visible_items):
        actual_index = visible_start + i
        lines.append(f"  {ListItem(item, actual_index)}")

    lines.append(f"{'-' * 70}")
    lines.append("")
    lines.append("操作说明:")
    lines.append("  ↑/k  向上滚动 10 项")
    lines.append("  ↓/j  向下滚动 10 项")
    lines.append("  PageUp   向上一页")
    lines.append("  PageDown 向下一页")
    lines.append("  Home     跳到顶部")
    lines.append("  End      跳到底部")
    lines.append("  q        退出")
    lines.append("")
    lines.append("并发渲染特性:")
    lines.append("  - 时间切片：长列表渲染会让出主线程")
    lines.append("  - 抢占式更新：滚动输入可以中断当前渲染")
    lines.append("  - 优先级调度：离散输入优先级高于渲染")

    return Text("\n".join(lines))


if __name__ == "__main__":
    from pyinkcli import Options, Ink

    # 创建 Ink 实例
    app = Ink(Options(
        stdout=__import__("sys").stdout,
        stdin=__import__("sys").stdin,
        stderr=__import__("sys").stderr,
        interactive=True,
        concurrent=True,  # 启用并发模式
        max_fps=60,  # 60 FPS
        incremental_rendering=True,  # 启用增量渲染
    ))

    # 渲染组件
    app.render(LargeList())

    # 等待退出
    app.wait_until_exit()
