"""
useDeferredValue 示例 - 演示延迟更新

这个示例展示了如何使用 useDeferredValue 来延迟非关键 UI 的更新，
让关键交互（如输入）保持流畅。

场景：搜索框 + 大型列表
- 输入是即时响应的（高优先级）
- 列表过滤是延迟的（低优先级）
"""

from pyinkcli import Text, useDeferredValue, useInput, useState, render


def SearchableList():
    """可搜索的列表组件"""
    # 生成 1000 个测试数据
    all_items = [f"Item {i} - Python 编程示例 {i * 10}" for i in range(1000)]

    # 当前输入的查询（高优先级，立即响应）
    query, set_query = useState("")

    # 延迟的查询值（低优先级，延迟更新）
    # 这样输入框立即响应，但列表过滤可以延迟
    deferred_query = useDeferredValue(query, initial_value="")

    # 根据延迟的查询过滤列表
    if deferred_query:
        filtered_items = [
            item for item in all_items
            if deferred_query.lower() in item.lower()
        ][:50]  # 最多显示 50 个结果
    else:
        filtered_items = all_items[:20]  # 默认显示前 20 个

    def handle_input(key, key_obj):
        if key == "q" or key == "Q":
            # 退出
            app.exit()
        elif len(key) == 1:
            # 单个字符输入
            set_query(query + key)
        elif key == "backspace":
            # 退格
            set_query(query[:-1] if query else "")
        elif key == "return":
            # 回车，开始搜索
            set_query(query)

    useInput(handle_input)

    # 构建输出
    lines = [
        f"{'=' * 60}",
        f"useDeferredValue 示例 - 搜索框 (按 'q' 退出)",
        f"{'=' * 60}",
        f"",
        f"当前输入：{query or '(空)'}",
        f"延迟查询：{deferred_query or '(空)'}",
        f"",
        f"{'-' * 60}",
        f"搜索结果 (共 {len(filtered_items)} 项):",
        f"{'-' * 60}",
    ]

    for item in filtered_items:
        lines.append(f"  {item}")

    if not query:
        lines.append("")
        lines.append("提示：开始输入来搜索列表...")
        lines.append("输入会立即显示，但列表过滤会延迟更新")
        lines.append("这样保证了输入流畅，不会卡顿")

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
        max_fps=30,  # 30 FPS 节流
    ))

    # 渲染组件
    app.render(SearchableList())

    # 等待退出
    app.wait_until_exit()
