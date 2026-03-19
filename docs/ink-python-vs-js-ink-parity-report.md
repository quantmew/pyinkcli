# ink-python 与 js_source/ink 对照汇报

## 结论摘要

当前仓库中的 `ink-python` **不是**对 `js_source/ink` 的逻辑、功能、代码进行了一比一严格翻译。

更准确的判断是：

- 目录结构、模块命名、部分组件和 hook 名称，明显参考了 Ink 的设计。
- 核心运行时语义、公开 API 契约、输入系统、reconciler、输出系统和测试覆盖，均未与 JS 版严格对齐。
- 当前 `ink-python` 更接近“参考 Ink 设计的 Python 版雏形”或“简化移植版”，而不是“严格等价移植”。

---

## 评级标准

- `已对齐`：语义和接口基本一致，可视为同等能力。
- `部分对齐`：概念和入口存在映射，但能力、边界行为或内部实现不完全一致。
- `缺失`：JS 版已有能力，Python 版没有实现，或只有占位接口。
- `明显偏差`：Python 版虽然有对应模块或接口，但核心语义和 JS 版差异很大。

---

## 总览

| 模块 | 评级 | 简述 |
|---|---|---|
| `render` | 明显偏差 | 公开实例契约、生命周期能力、stdout 实例复用都不同 |
| `renderer` | 部分对齐 | 都有 DOM -> 输出主路径，但 JS 明显更完整 |
| `reconciler` | 明显偏差 | Python 是整树重建；JS 是真正的 React reconciler |
| `hooks` | 明显偏差 | 名称有映射，但 hooks 运行时模型差异很大 |
| `components` | 部分对齐 | 基础组件入口大体对应，但根组件能力差距大 |
| `input` | 明显偏差 | Python 输入解析、事件系统、kitty/paste 能力远弱于 JS |
| `output` | 明显偏差 | ANSI、增量更新、局部更新能力不对等 |
| `tests` | 明显偏差 | 覆盖范围和深度差距很大 |

---

## 1. Render

| 子模块 | 评级 | 说明 |
|---|---|---|
| `render()` 主入口 | 明显偏差 | JS `render()` 返回 `Instance`，包含 `rerender`、`unmount`、`waitUntilExit`、`waitUntilRenderFlush`、`cleanup`、`clear`；Python 直接返回 `Ink` 实例，没有同等契约。[render.ts](/mnt/hdd1/ink-python/js_source/ink/src/render.ts#L138) [ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L683) |
| `Ink` 生命周期 | 部分对齐 | 两边都有 `render/unmount/clear/wait until exit` 一类概念，但 Python 缺 `waitUntilRenderFlush`、stdout 实例管理、console patch 清理等能力。[ink.tsx](/mnt/hdd1/ink-python/js_source/ink/src/ink.tsx#L874) [ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L273) |
| `concurrent` 支持 | 缺失 | Python `Options` 有字段，但 `is_concurrent` 直接固定返回 `False`。[ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L68) [ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L185) |
| `patch_console` | 缺失 | Python 有选项但没有对应运行时实现；JS 有完整 patch/restore 流程。[ink.tsx](/mnt/hdd1/ink-python/js_source/ink/src/ink.tsx#L429) [ink.tsx](/mnt/hdd1/ink-python/js_source/ink/src/ink.tsx#L931) |
| `alternate screen` | 部分对齐 | Python 和 JS 都有该选项和基础启停逻辑，但 JS 对 teardown、实例复用、stdout 状态处理更完整。[ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L610) [ink.tsx](/mnt/hdd1/ink-python/js_source/ink/src/ink.tsx#L952) |
| `renderToString()` | 明显偏差 | JS 主要是 `columns` 语义；Python 增加了 `rows` 高度裁剪模型，API 和行为都不是同一设计。[render-to-string.ts](/mnt/hdd1/ink-python/js_source/ink/src/render-to-string.ts#L8) [render_to_string.py](/mnt/hdd1/ink-python/src/pyinkcli/render_to_string.py#L38) |

### Render 小结

- 有名称和流程层面的映射。
- 没有做到 JS 版实例契约和生命周期能力的严格一致。

---

## 2. Renderer

| 子模块 | 评级 | 说明 |
|---|---|---|
| DOM -> 输出总流程 | 部分对齐 | 两边都有 `render(node)` -> `output/static_output/output_height` 结构。[renderer.py](/mnt/hdd1/ink-python/src/pyinkcli/renderer.py#L31) |
| screen reader 输出 | 部分对齐 | Python 有专门分支，但 hook 和上下文侧没有打通完整能力；JS 是整条链路贯通的。[renderer.py](/mnt/hdd1/ink-python/src/pyinkcli/renderer.py#L45) [ink.tsx](/mnt/hdd1/ink-python/js_source/ink/src/ink.tsx#L627) |
| `<Static>` 处理 | 部分对齐 | Python 有 `static_output` 概念；JS 则配合 reconciler 的 immediate render 和 cleanup 语义更完整。[renderer.py](/mnt/hdd1/ink-python/src/pyinkcli/renderer.py#L56) [reconciler.ts](/mnt/hdd1/ink-python/js_source/ink/src/reconciler.ts#L167) |
| 渲染刷新时机 | 明显偏差 | Python 的渲染触发与 reconciler/节流逻辑较简化；JS 有 commit 后渲染、静态内容即时渲染、flush 等更完整机制。[ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L298) [reconciler.ts](/mnt/hdd1/ink-python/js_source/ink/src/reconciler.ts#L160) |

### Renderer 小结

- Python 版已经具备基础渲染通路。
- 但刷新语义、静态内容处理、屏幕阅读器完整性仍与 JS 有较大差距。

---

## 3. Reconciler

| 子模块 | 评级 | 说明 |
|---|---|---|
| 容器更新 | 明显偏差 | Python `update_container()` 先删光全部 children 再重新建树；不是增量 reconciler。[reconciler.py](/mnt/hdd1/ink-python/src/pyinkcli/reconciler.py#L59) |
| Host config / commit update | 缺失 | JS 有 `commitUpdate`、`commitTextUpdate`、`hide/unhide`、`insertBefore`、`removeChildFromContainer` 等完整 host config；Python 没有同等级机制。[reconciler.ts](/mnt/hdd1/ink-python/js_source/ink/src/reconciler.ts#L298) |
| Text/Box 约束 | 已对齐 | `<Text>` 内不能嵌 `<Box>`、裸文本必须在 `<Text>` 内，这些基础规则两边都有。[reconciler.py](/mnt/hdd1/ink-python/src/pyinkcli/reconciler.py#L148) [reconciler.ts](/mnt/hdd1/ink-python/js_source/ink/src/reconciler.ts#L194) |
| Fragment 处理 | 部分对齐 | 两边都有 Fragment 概念，但 Python 是手工展开，不是 React Fiber 语义级别实现。[reconciler.py](/mnt/hdd1/ink-python/src/pyinkcli/reconciler.py#L175) |
| 并发调度 / Scheduler | 缺失 | JS 集成 `scheduler` 和 React event priority；Python 没有。[reconciler.ts](/mnt/hdd1/ink-python/js_source/ink/src/reconciler.ts#L275) |

### Reconciler 小结

- 这是当前差距最大的核心模块之一。
- Python 版并不是对 JS reconciler 的语义翻译，而是一个简化的“重建整树”实现。

---

## 4. Hooks

| 子模块 | 评级 | 说明 |
|---|---|---|
| `useApp` | 明显偏差 | JS 主要暴露 `exit()`、`waitUntilRenderFlush()`；Python 是 `exit()`、`wait_until_exit()`、`clear()`、`on_exit()`，接口设计已经不同。[use-app.ts](/mnt/hdd1/ink-python/js_source/ink/src/hooks/use-app.ts#L1) [use_app.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_app.py#L15) |
| `useInput` | 明显偏差 | JS 基于 stdin context + effect + raw mode + discreteUpdates；Python 是全局 handler 列表，`is_active` 没真正参与分发控制。[use-input.ts](/mnt/hdd1/ink-python/js_source/ink/src/hooks/use-input.ts#L159) [use_input.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_input.py#L76) |
| `usePaste` | 缺失 | Python API 名称存在，但调用了不存在的方法，当前实现并未真正打通。[use_paste.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_paste.py#L43) [use_stdin.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_stdin.py#L13) |
| `useStdin` | 明显偏差 | JS 是上下文接口，支持 `setRawMode`、`setBracketedPasteMode`、事件总线；Python 是简化 `StdinHandle`。[StdinContext.ts](/mnt/hdd1/ink-python/js_source/ink/src/components/StdinContext.ts#L12) [use_stdin.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_stdin.py#L13) |
| `useStdout` / `useStderr` | 部分对齐 | 都提供访问流的能力，但 JS 与输出恢复、patch console、重绘更紧密集成。 |
| `useCursor` | 部分对齐 | 都有控制光标可见性，但 JS 会配合 App 生命周期和并发副作用处理；Python 更直接。 |
| `useFocus` / `useFocusManager` | 部分对齐 | 有 API 对应，但底层焦点系统和原始输入事件体系不等价。 |
| `useWindowSize` | 部分对齐 | 概念对齐，但 Python resize 触发和实例管理更简化。 |
| `useIsScreenReaderEnabled` | 缺失 | Python hook 直接写死返回 `False`，不具备 JS 的真实能力。[use_is_screen_reader_enabled.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_is_screen_reader_enabled.py#L10) |
| `useBoxMetrics` | 部分对齐 | 两边都有该 hook，但 Python 底层 DOM/layout listener 机制较简化。 |
| `useState/useEffect/useRef/useMemo/useCallback` | 明显偏差 | Python 暴露了这些 React 风格 hooks，但实现是全局单一状态，不是组件级 hooks 语义。[state.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/state.py#L27) |

### Hooks 小结

- 名称对齐很多。
- 但运行时语义、生命周期绑定方式、状态模型和事件系统与 JS 版存在根本差异。

---

## 5. Components

| 子模块 | 评级 | 说明 |
|---|---|---|
| `Box` | 部分对齐 | 名称、基础 props 映射、样式入口大体对应。[box.py](/mnt/hdd1/ink-python/src/pyinkcli/components/box.py) |
| `Text` | 部分对齐 | 基本文本与样式能力对齐一部分，但最终输出处理能力不如 JS 完整。 |
| `Static` | 部分对齐 | 有组件和静态输出概念，但与 reconciler/renderer 的联动没有 JS 完整。 |
| `Transform` | 部分对齐 | 都有该组件入口。 |
| `Newline` / `Spacer` | 已对齐 | 这类简单基础组件语义基本一致。 |
| `App` 根组件 | 明显偏差 | JS `App` 负责 raw mode、stdin/stdout/stderr context、cursor、focus、paste、cleanup 等核心运行时；Python `App` 明显是简化版。[App.tsx](/mnt/hdd1/ink-python/js_source/ink/src/components/App.tsx#L26) [app.py](/mnt/hdd1/ink-python/src/pyinkcli/components/app.py#L20) |
| Error boundary / accessibility context / background context | 缺失 | JS 有这些内部组件；Python 没有同等模块。[js_source/ink/src/components](/mnt/hdd1/ink-python/js_source/ink/src/components) |

### Components 小结

- 基础视觉组件的入口大体对得上。
- 根组件与内部上下文组件体系没有做到对齐。

---

## 6. Input

| 子模块 | 评级 | 说明 |
|---|---|---|
| keypress 解析 | 明显偏差 | Python `_parse_keypress()` 只覆盖少量 ANSI 序列；JS `parse-keypress` 支持更复杂情况和 kitty protocol。[use_input.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_input.py#L119) [parse-keypress.ts](/mnt/hdd1/ink-python/js_source/ink/src/parse-keypress.ts#L425) |
| 输入 chunk 处理 | 缺失 | JS 有 `input-parser` 专门解决 escape/paste/delete repeat/chunk 边界；Python 没有对应层。[input-parser.ts](/mnt/hdd1/ink-python/js_source/ink/src/input-parser.ts#L200) |
| kitty keyboard | 缺失 | Python 只有选项字段，没有解析、探测、启用链路；JS 是完整支持。[ink.py](/mnt/hdd1/ink-python/src/pyinkcli/ink.py#L69) [ink.tsx](/mnt/hdd1/ink-python/js_source/ink/src/ink.tsx#L1092) |
| raw mode 管理 | 部分对齐 | Python `useStdin` 里有基础 `set_raw_mode()`；但缺少 JS 那套引用计数、上下文协调和 hook 生命周期管理。[use_stdin.py](/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_stdin.py#L36) [App.tsx](/mnt/hdd1/ink-python/js_source/ink/src/components/App.tsx#L71) |
| bracketed paste | 缺失 | JS 有；Python 未打通。 |

### Input 小结

- 当前 Python 版输入系统只能覆盖部分基础按键场景。
- 复杂终端输入语义和生产级稳定性与 JS 版差距明显。

---

## 7. Output

| 子模块 | 评级 | 说明 |
|---|---|---|
| `Output` 缓冲 | 明显偏差 | Python 是二维字符串网格，注释里就承认不完整处理 ANSI；JS 有 styled chars、ANSI tokenizer、slice-ansi 等更完整实现。[output.py](/mnt/hdd1/ink-python/src/pyinkcli/output.py#L181) |
| `log_update` | 明显偏差 | Python 虽有 `incremental` 参数，但没有 JS 那种标准/增量两套写屏策略与局部更新能力。[log_update.py](/mnt/hdd1/ink-python/src/pyinkcli/log_update.py#L20) [log-update.ts](/mnt/hdd1/ink-python/js_source/ink/src/log-update.ts#L31) |
| write synchronization | 缺失 | JS 有 `write-synchronized` 和条件同步输出；Python 没有同等级模块。[write-synchronized.ts](/mnt/hdd1/ink-python/js_source/ink/src/write-synchronized.ts#L1) |
| ANSI sanitize/tokenize/background/border rendering | 缺失 | JS 有 `ansi-tokenizer`、`sanitize-ansi`、`render-background`、`render-border`；Python 没有对应模块或仅分散简化实现。 |
| screen reader 输出 | 部分对齐 | Python 有对应渲染分支，但不是完整功能链。 |

### Output 小结

- Python 版已经能完成基础字符渲染。
- 但 ANSI 语义、局部更新、同步输出和复杂视觉处理能力明显弱于 JS。

---

## 8. Tests

| 子模块 | 评级 | 说明 |
|---|---|---|
| 测试数量 | 明显偏差 | JS `ink` 测试约 45 个文件；Python 当前只有少量测试文件。 |
| 组件基础测试 | 部分对齐 | Python 对 `Box/Text/string_width/ansi helpers` 有基础测试。[test_box.py](/mnt/hdd1/ink-python/tests/test_box.py#L1) |
| hooks 测试 | 明显偏差 | Python hooks 测试主要是静态 API 级别；JS 覆盖真实终端行为、输入、离散优先级、stdout/stderr、focus 等。[test_hooks.py](/mnt/hdd1/ink-python/tests/test_hooks.py#L1) [hooks-use-input.tsx](/mnt/hdd1/ink-python/js_source/ink/test/hooks-use-input.tsx#L1) |
| render/reconciler/log-update/input-parser/kitty/alternate-screen | 缺失 | 这些 JS 都有较完整测试，Python 基本没有同等覆盖。[js_source/ink/test](/mnt/hdd1/ink-python/js_source/ink/test) |
| screen reader / errors / overflow / layout edge cases | 缺失 | Python 目前看不到与 JS 对应的系统性测试。 |

### Tests 小结

- 现有 Python 测试无法支撑“行为严格一致”的结论。
- 如果要追求 parity，测试补齐必须和功能补齐同步进行。

---

## 按评级汇总

### 已对齐

- `reconciler` 中的基础文本约束：
  - 裸字符串必须在 `<Text>` 中
  - `<Text>` 内不能嵌 `<Box>`
- 简单组件：
  - `Newline`
  - `Spacer`
- 少部分表层 API 命名：
  - `Box`
  - `Text`
  - `Static`
  - `Transform`
  - `useInput`
  - `useFocus`

### 部分对齐

- `renderer`
- `alternate screen`
- `Box` / `Text` / `Static` / `Transform`
- `useStdout` / `useStderr` / `useCursor` / `useWindowSize` / `useFocus` / `useFocusManager` / `useBoxMetrics`
- screen reader 渲染分支
- raw mode 的最基础能力
- 一些基础测试

### 缺失

- `concurrent`
- `waitUntilRenderFlush`
- `cleanup` 实例契约
- `patch_console`
- kitty keyboard 完整支持
- `input-parser`
- bracketed paste 真正实现
- `write-synchronized`
- `ansi-tokenizer` / `sanitize-ansi` / `render-background` / `render-border`
- `useIsScreenReaderEnabled` 真实能力
- 大量运行时测试

### 明显偏差

- `render()` 整体公开契约
- `reconciler` 核心实现
- hooks 运行时模型
- `App` 根组件职责
- 输入事件系统
- 输出缓冲与 `log_update`
- 测试矩阵整体

---

## 最终判断

如果目标是评估“`ink-python` 是否已经和 `js_source/ink` 严格一致”，答案是否定的。

如果目标是继续推进 parity，建议把后续工作优先级放在以下几个方向：

1. `reconciler` 与 hooks 运行时模型
2. `render()` 实例契约与生命周期补齐
3. `input-parser`、raw mode、paste、kitty keyboard
4. `Output` / `log_update` / ANSI 渲染链
5. 与 JS 侧一一对应的测试补齐

这些模块不补齐，`ink-python` 无法被视为 JS Ink 的严格等价实现。
