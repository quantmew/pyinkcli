# Naming Parity Audit

基于当前仓库代码重新审计：

- `js_source/ink/src`
- `src/ink_python`

本次只看 4 件事：

1. 哪些文件名还不是一比一。
2. 哪些文件的顶层函数、类、变量名还不是一比一。
3. 哪些文件虽然有对应文件，但顺序、职责、公开面还不是一一对应。
4. `examples` 现在是否可运行。

## 1. 文件名不是一比一对应的地方

### 1.1 JS 有、Python 现在已补齐

`get-max-width.ts` 这轮已补成 [get_max_width.py](/mnt/hdd1/ink-python/src/ink_python/get_max_width.py)。

到当前代码为止，`js_source/ink/src` 的运行时文件已经都能在 `src/ink_python` 找到规范化后的同名 Python 文件。

### 1.2 仍然不是“严格一文件对一文件”的地方

这些不是“缺文件”，而是“多文件 / 额外文件 / 包装文件”问题：

| Python 文件 | 对应情况 | 结论 |
|---|---|---|
| [__init__.py](/mnt/hdd1/ink-python/src/ink_python/__init__.py) | JS 没有包级 `__init__` | Python 包装层，非一比一 |
| [component.py](/mnt/hdd1/ink-python/src/ink_python/component.py) | JS 侧 React/runtime 分散提供 | Python 额外兼容层，非一比一 |
| [components/Suspense.py](/mnt/hdd1/ink-python/src/ink_python/components/Suspense.py) | JS `index.ts` 当前不导出 `Suspense` | Python 扩展面 |
| [hooks/state.py](/mnt/hdd1/ink-python/src/ink_python/hooks/state.py) | JS hooks runtime 来自 React 本身 | Python 自建 hooks 状态层 |
| [hooks/use_transition.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_transition.py) | JS 当前 `src` 没有同名文件 | Python 扩展面 |
| [suspense_runtime.py](/mnt/hdd1/ink-python/src/ink_python/suspense_runtime.py) | JS Suspense 由 React/reconciler 支撑 | Python 额外运行时层 |
| [yoga_compat.py](/mnt/hdd1/ink-python/src/ink_python/yoga_compat.py) | JS 直接用 `yoga-layout` | Python Yoga 适配层 |
| [utils/ansi_escapes.py](/mnt/hdd1/ink-python/src/ink_python/utils/ansi_escapes.py) | 对应外部依赖 `ansi-escapes`，不在 `ink/src` | Python 额外包装 |
| [utils/cli_boxes.py](/mnt/hdd1/ink-python/src/ink_python/utils/cli_boxes.py) | 对应外部依赖 `cli-boxes`，不在 `ink/src` | Python 额外包装 |
| [utils/string_width.py](/mnt/hdd1/ink-python/src/ink_python/utils/string_width.py) | 对应外部依赖 `string-width`，不在 `ink/src` | Python 额外包装 |
| [utils/wrap_ansi.py](/mnt/hdd1/ink-python/src/ink_python/utils/wrap_ansi.py) | 对应外部依赖 `wrap-ansi`，不在 `ink/src` | Python 额外包装 |

## 2. 顶层函数、类、变量名不是一比一对应的地方

这里看的是“模块顶层公开名”，不是函数内部局部变量。

### 2.1 同语义，但名字仍不是 JS 原名

| JS 文件 | Python 文件 | 现状 |
|---|---|---|
| `cursor-helpers.ts` | [cursor_helpers.py](/mnt/hdd1/ink-python/src/ink_python/cursor_helpers.py) | 公开的是 `cursor_position_changed` / `build_cursor_suffix` / `build_return_to_bottom` / `build_cursor_only_sequence` / `build_return_to_bottom_prefix`，不是 JS 的 camelCase |
| `render-node-to-output.ts` | [render_node_to_output.py](/mnt/hdd1/ink-python/src/ink_python/render_node_to_output.py) | 公开的是 `render_node_to_output` / `render_node_to_screen_reader_output`，不是 JS 的 `renderNodeToOutput` / `renderNodeToScreenReaderOutput` |
| `dom.ts` | [dom.py](/mnt/hdd1/ink-python/src/ink_python/dom.py) | 同时存在 `createNode` / `createTextNode` / `appendChildNode` 等 camelCase，以及 `add_layout_listener` / `emit_layout_listeners` 这类 snake_case 漂移 |

### 2.2 Python 多暴露了额外公开面

| 文件 | 额外公开名 |
|---|---|
| [index.py](/mnt/hdd1/ink-python/src/ink_python/index.py) | `Suspense`, `useTransition`, `DOMElement`, `Key` |
| [__init__.py](/mnt/hdd1/ink-python/src/ink_python/__init__.py) | `Ink`, `createElement`, `component`, `useState`, `useEffect`, `useRef`, `useMemo`, `useCallback` 等一整层 Python 包装导出 |
| [render_to_string.py](/mnt/hdd1/ink-python/src/ink_python/render_to_string.py) | `create_root_node` |
| [log_update.py](/mnt/hdd1/ink-python/src/ink_python/log_update.py) | `create`, `createStandard`, `createIncremental`, `createLogUpdate` 全部公开；JS 默认导出模型不同 |
| [styles.py](/mnt/hdd1/ink-python/src/ink_python/styles.py) | `Styles`、多组 `Literal` 类型别名、`apply_styles`；JS 是 `styles` 常量集合 |
| [components/AppContext.py](/mnt/hdd1/ink-python/src/ink_python/components/AppContext.py) | `get_app_context`, `set_app_context`, `provide_app_context` |
| [components/AccessibilityContext.py](/mnt/hdd1/ink-python/src/ink_python/components/AccessibilityContext.py) | `provide_accessibility`, `is_screen_reader_enabled` |
| [components/BackgroundContext.py](/mnt/hdd1/ink-python/src/ink_python/components/BackgroundContext.py) | `provide_background_color`, `get_background_color` |
| [components/StdinContext.py](/mnt/hdd1/ink-python/src/ink_python/components/StdinContext.py) | `provide_stdin`, `get_stdin` |
| [components/StdoutContext.py](/mnt/hdd1/ink-python/src/ink_python/components/StdoutContext.py) | `provide_stdout`, `get_stdout` |
| [components/StderrContext.py](/mnt/hdd1/ink-python/src/ink_python/components/StderrContext.py) | `provide_stderr`, `get_stderr` |
| [hooks/use_focus.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_focus.py) | `focusNext`, `focusPrev` |

### 2.3 职责相近，但公开形态还不是 JS 那个形状

| JS 文件 | Python 文件 | 现状 |
|---|---|---|
| `output.ts` | [output.py](/mnt/hdd1/ink-python/src/ink_python/output.py) | JS 是默认导出类；Python 是 `Output` 类，没有“默认导出”语义 |
| `ink.tsx` | [ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py) | JS 默认导出 `Ink` 组件语义；Python 是 `Ink` 运行时类，公开面更偏实例管理 |
| `components/ErrorBoundary.tsx` | [components/ErrorBoundary.py](/mnt/hdd1/ink-python/src/ink_python/components/ErrorBoundary.py) | 文件名对上了，但 JS 是 React class component 语义，Python 不是同构形态 |
| `components/Text.tsx` / `Static.tsx` / `Transform.tsx` / `Newline.tsx` / `Spacer.tsx` | 同名 `.py` | Python 是函数式工厂组件，不存在 TS 默认导出 + props type 那一套同构公开面 |

## 3. 文件顺序、职责、功能还不是一一对应的地方

这个问题比“名字”更关键。现在主要是 4 类。

### 3.1 入口文件顺序不一致

- [index.ts](/mnt/hdd1/ink-python/js_source/ink/src/index.ts) 的导出顺序是 `render -> renderToString -> Box -> Text -> ... -> kitty flags`。
- [index.py](/mnt/hdd1/ink-python/src/ink_python/index.py) 结构大体跟随了 JS，但额外插入了 `Suspense`、`useTransition`、`DOMElement`、`Key`。
- [__init__.py](/mnt/hdd1/ink-python/src/ink_python/__init__.py) 又叠加了一层更大的 Python 包装导出面，已经不是 JS 单入口模型。

结论：入口文件不是严格一一对应，而是“JS 单入口 + Python 双入口 + Python 额外导出”。

### 3.2 `render-node-to-output` 仍混入了额外职责

[render-node-to-output.ts](/mnt/hdd1/ink-python/js_source/ink/src/render-node-to-output.ts) 依赖独立的 `get-max-width.ts`。

[render_node_to_output.py](/mnt/hdd1/ink-python/src/ink_python/render_node_to_output.py) 这轮已改为复用独立的 [get_max_width.py](/mnt/hdd1/ink-python/src/ink_python/get_max_width.py)，但它仍然额外公开：

- `applyPaddingToText`
- `indentString`

结论：主职责更接近了，但文件公开面仍比 JS 更宽。

### 3.3 Context 文件更像“上下文 + 访问器”而不是单纯 context 值

JS 的 `AppContext.ts` / `StdinContext.ts` / `StdoutContext.ts` / `StderrContext.ts` / `BackgroundContext.ts` 更偏 React context 定义。

Python 对应文件同时承载：

- 当前 context 值
- getter / setter / provider
- 运行时共享状态

结论：文件名对应了，但职责层次仍然合并得更厚。

### 3.4 Hooks/runtime 仍不是 JS 的层次拆分

- JS 的 hooks 语义很大程度来自 React。
- Python 通过 [hooks/state.py](/mnt/hdd1/ink-python/src/ink_python/hooks/state.py)、[suspense_runtime.py](/mnt/hdd1/ink-python/src/ink_python/suspense_runtime.py)、[component.py](/mnt/hdd1/ink-python/src/ink_python/component.py) 自己补了一层 runtime。

结论：`useApp` / `useInput` / `useFocus` 等文件名虽然对应，但底层职责拆分并不是 JS 那个一层层依赖关系。

## 4. examples 现在能不能正常使用

当前结论：

- `js_source/ink/examples` 25 个目录，Python 侧都已补齐对应目录。
- 运行 `pytest -q tests/test_examples_directory_parity.py tests/test_examples_smoke.py`，结果是 `23 passed in 36.14s`。

也就是说：

- 目录映射：通过
- smoke 运行：通过

但这不等于“功能语义完全和 JS 一致”。当前 smoke 只能证明：

- 示例入口存在
- 示例能启动
- 关键文本能输出

不能证明：

- 交互行为完全一致
- 并发 / Suspense / IME / screen reader 语义完全一致
- 与 JS 逐帧输出完全一致

## 当前最值得继续收敛的点

如果下一步继续按“一比一翻译复刻”推进，优先级建议是：

1. 收窄 [index.py](/mnt/hdd1/ink-python/src/ink_python/index.py) 和 [__init__.py](/mnt/hdd1/ink-python/src/ink_python/__init__.py) 的额外公开面。
2. 把 [cursor_helpers.py](/mnt/hdd1/ink-python/src/ink_python/cursor_helpers.py) 和 [render_node_to_output.py](/mnt/hdd1/ink-python/src/ink_python/render_node_to_output.py) 的 snake_case 公开名收回到 JS 同名公开名。
3. 继续拆薄各个 `*Context.py`，避免把 “context 定义 + provider + getter/setter” 混在一个文件里。
4. 明确决定 `Suspense` / `useTransition` 是否要保持为 Python 扩展面；如果目标是严格跟随 `js_source/ink/src/index.ts`，这两个导出需要重新评估。
