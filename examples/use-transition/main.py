"""
useTransition 示例 - 演示过渡更新

这个示例展示了如何使用 useTransition 来标记低优先级的更新，
让高优先级的交互（如 Tab 切换）可以抢占。

场景：Tab 切换 + 大型列表渲染
- Tab 切换是高优先级（立即响应）
- 列表渲染是低优先级（可被抢占）
"""

from pyinkcli import Text, useTransition, useState, useInput, render


def TabContent(tab_name):
    """Tab 内容组件 - 模拟大型列表渲染"""
    # 模拟大量数据
    items = [f"[{tab_name}] Item {i} - 数据行 {i * 100}" for i in range(200)]

    lines = []
    for item in items:
        lines.append(f"  {item}")

    return Text("\n".join(lines))


def Tabs():
    """Tab 切换组件"""
    tabs = ["首页", "消息", "设置", "关于"]
    active_tab, set_active_tab = useState(0)

    # useTransition 返回 [isPending, startTransition]
    is_pending, start_transition = useTransition()

    def handle_input(key, key_obj):
        if key == "q" or key == "Q":
            # 退出
            app.exit()
        elif key == "left":
            # 上一个 Tab
            new_tab = max(0, active_tab - 1)

            # 使用 transition 包裹低优先级更新
            def update_tab():
                set_active_tab(new_tab)

            start_transition(update_tab)
        elif key == "right":
            # 下一个 Tab
            new_tab = min(len(tabs) - 1, active_tab + 1)

            # 使用 transition 包裹低优先级更新
            def update_tab():
                set_active_tab(new_tab)

            start_transition(update_tab)

    useInput(handle_input)

    # 构建 Tab 栏
    tab_bar_parts = []
    for i, tab in enumerate(tabs):
        if i == active_tab:
            tab_bar_parts.append(f" [{tab}] ")
        else:
            tab_bar_parts.append(f"  {tab}  ")

    tab_bar = "".join(tab_bar_parts)

    # 状态提示
    pending_indicator = " (更新中...)" if is_pending else ""

    lines = [
        f"{'=' * 60}",
        f"useTransition 示例 - Tab 切换 (按 'q' 退出)",
        f"{'=' * 60}",
        f"",
        f"使用 ← → 键切换 Tab{pending_indicator}",
        f"",
        f"{'-' * 60}",
        tab_bar,
        f"{'-' * 60}",
        f"",
        f"当前 Tab: {tabs[active_tab]}",
        f"",
    ]

    # 渲染当前 Tab 内容
    content_node = TabContent(tabs[active_tab])

    return Text("\n".join(lines)) + content_node


if __name__ == "__main__":
    from pyinkcli import Options, Ink

    # 创建 Ink 实例
    app = Ink(Options(
        stdout=__import__("sys").stdout,
        stdin=__import__("sys").stdin,
        stderr=__import__("sys").stderr,
        interactive=True,
        concurrent=True,  # 启用并发模式
        max_fps=30,  # 30 FPS 节流
    ))

    # 渲染组件
    app.render(Tabs())

    # 等待退出
    app.wait_until_exit()
