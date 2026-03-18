# Examples Parity Status

基于当前仓库实测：

- JS 目录：`js_source/ink/examples`
- Python 目录：`examples`
- 验证命令：`pytest -q tests/test_examples_directory_parity.py tests/test_examples_smoke.py`

结果：

- 目录对齐：通过
- smoke 运行：通过
- 总计：`23 passed in 36.14s`

## 结论

当前 `examples` 可以认为“都能正常启动并完成基础输出”。

这轮已经确认：

- JS 25 个 example 目录，Python 全部有对应目录。
- `select-input`
- `alternate-screen`
- `static`
- `subprocess-output`
- `use-transition`
- `cursor-ime`
- `suspense`
- `concurrent-suspense`
- `aria`
- `box-backgrounds`
- `router`
- `incremental-rendering`
- `jest`
- `use-focus`
- `use-focus-with-id`
- `use-stdout`
- `use-stderr`
- `terminal-resize`
- `table`
- `borders`
- `chat`

这些都已经被 smoke test 实际跑过。

## 仍然要注意

`smoke passed` 只表示：

- 文件存在
- 入口可以运行
- 输出包含关键文本

它不表示：

- 和 JS 的交互细节逐项一致
- `Suspense` / `useTransition` / IME / screen reader 完全等价
- 实时刷新与输入处理完全等价

如果后续要把 `examples` 进一步提升到“严格 parity”，下一步应该增加：

1. 带输入事件的集成测试。
2. 对关键示例的逐帧输出快照。
3. 对 `alternate-screen`、`cursor-ime`、`use-transition`、`concurrent-suspense` 的行为级测试。
