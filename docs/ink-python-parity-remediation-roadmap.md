# ink-python Parity 整改路线图

## 目标

这份路线图用于回答一个具体问题：

> 如果要把 `ink-python` 逐步拉近到 `js_source/ink` 的行为与功能水平，应该先修什么，后修什么？

这里不追求“理论上完整”，而是按 **兼容性收益、架构阻塞程度、测试可落地性** 排优先级。

优先级定义如下：

- `P0`：必须优先处理。属于核心架构或关键兼容性阻塞项，不解决会导致后续 parity 工作建立在错误基础上。
- `P1`：高优先级。直接影响重要功能兼容性和用户行为，但依赖 `P0` 先打底。
- `P2`：增强项。提升完整度、体验和边界兼容性，但不应先于 `P0/P1`。

---

## 总体原则

整改顺序建议遵循以下原则：

1. **先修运行时骨架，再补功能表层**
2. **先修实例契约和状态模型，再补输入输出细节**
3. **每补一类能力，就同步补对应测试**
4. **避免继续在“简化 runtime”上堆更多 API 占位**

---

## P0：核心阻塞项

## P0-1. 重构 hooks 运行时模型

### 目标

把当前全局单一 `HookState` 模型，改成至少按组件实例维护的 hooks 状态模型。

### 当前问题

- 当前 `useState/useEffect/useRef/useMemo/useCallback` 建立在一个全局 `_current_state` 上。[state.py](/mnt/hdd1/ink-python/src/ink_python/hooks/state.py#L27)
- 这和 React/Ink 的组件级 hooks 语义不一致。
- 在当前模型下，复杂组件树、嵌套组件、重渲染顺序变化时，很难保证状态正确性。

### 为什么是 P0

如果 hooks 状态模型不重构，后面的 `useInput`、`useFocus`、`usePaste`、`useBoxMetrics`、`useEffect cleanup` 都只能停留在“看起来像 API 一样”，无法真正靠近 JS 行为。

### 建议交付

- 为每个函数组件实例维护独立 hook state
- 明确 render 阶段与 commit 阶段的 effect 执行边界
- 支持 effect cleanup 的稳定生命周期
- 建立最小可用的 hooks 顺序校验机制

### 对应测试

- 组件嵌套时 state 不串扰
- rerender 后 state 保持
- effect 在依赖变化时触发，cleanup 正确执行
- 多组件同时使用 hooks 时行为稳定

---

## P0-2. 重构 reconciler，从“整树重建”走向“增量更新”

### 目标

让 Python reconciler 不再每次 `update_container()` 都清空整棵树重建，而是支持最基本的增量更新。

### 当前问题

- 当前 `update_container()` 会先移除所有 children，再重建整个树。[reconciler.py](/mnt/hdd1/ink-python/src/ink_python/reconciler.py#L75)
- 这和 JS 版基于 `react-reconciler` 的 `commitUpdate`、`insertBefore`、`removeChild` 等机制不是一个层级。[reconciler.ts](/mnt/hdd1/ink-python/js_source/ink/src/reconciler.ts#L298)
- `<Static>`、layout listener、focus、cursor、输入副作用等都很容易在整树重建中被破坏。

### 为什么是 P0

reconciler 是所有行为一致性的基础。如果仍然整树重建，那么很多 JS 语义即使“API 看起来补上了”，行为仍然不可能对齐。

### 建议交付

- 增加节点级 diff/update 机制
- 支持 props 更新而不是销毁重建
- 支持文本节点更新
- 支持 child 插入、删除、重排
- 为 `<Static>` 和 layout 计算保留稳定节点身份

### 对应测试

- prop 更新不导致整树丢失
- 文本更新只更新文本节点
- child reorder 行为正确
- 静态节点在增量更新中行为稳定

---

## P0-3. 对齐 `render()` / `Ink` 实例契约

### 目标

把 Python 对外公开的实例行为收敛到更接近 JS Ink 的契约。

### 当前问题

- JS `render()` 返回 `Instance`，有 `rerender`、`unmount`、`waitUntilExit`、`waitUntilRenderFlush`、`cleanup`、`clear`。[render.ts](/mnt/hdd1/ink-python/js_source/ink/src/render.ts#L138)
- Python `render()` 直接返回 `Ink` 实例，缺 `waitUntilRenderFlush`、`cleanup` 等能力。[ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py#L683)

### 为什么是 P0

实例契约是上层用户和测试系统依赖的基础。如果这里不先收敛，很多 JS 侧测试和用法无法映射过来。

### 建议交付

- 补 `wait_until_render_flush`
- 明确 `cleanup` 语义
- 明确 `rerender` 与 `render` 的公开约定
- 明确 `unmount` 何时完成 stdout flush
- 统一 Python 命名与 JS 命名策略，决定是否保留 snake_case/camelCase 双出口

### 对应测试

- rerender 后可等待 flush
- unmount 后实例状态正确
- cleanup 后同一 stdout 可重建实例
- clear 在 interactive/non-interactive 下行为可验证

---

## P0-4. 补齐输入系统骨架：input parser、raw mode、事件分发

### 目标

把输入系统从“简化按键解析”提升到“可承载 Ink hooks 行为”的基础设施。

### 当前问题

- Python 目前只有简化 `_parse_keypress()`。[use_input.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_input.py#L119)
- 没有 JS `input-parser` 那种处理 chunk 边界、ESC 前缀、delete repeat、paste 边界的层。[input-parser.ts](/mnt/hdd1/ink-python/js_source/ink/src/input-parser.ts#L200)
- `usePaste()` 所依赖的 bracketed paste 机制没有打通。[use_paste.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_paste.py#L43)

### 为什么是 P0

输入系统是 `useInput/usePaste/useFocus/useFocusManager` 的基础。没有这一层，hooks 再怎么补都不稳定。

### 建议交付

- 增加独立 input parser 层
- 正确处理 chunked escape sequences
- 区分 typed input 与 non-printable keys
- 建立内部事件总线：`input` / `paste`
- 统一 raw mode 开关入口，避免各 hook 直接各自管理底层流

### 对应测试

- 普通字符、Ctrl、Meta、Tab、Delete、Escape
- ESC 前缀分块输入
- 长按 delete/backspace 的重复输入
- bracketed paste 与 typed input 分流

---

## P0-5. 建立 parity 测试基线

### 目标

在 Python 侧建立一套和 JS 关键能力一一映射的最小 parity 测试集。

### 当前问题

- Python 测试覆盖较少，主要是基础 API 和工具函数。[tests](/mnt/hdd1/ink-python/tests)
- JS 侧覆盖 render、reconciler、log-update、input、alternate screen、screen reader 等完整链路。[js_source/ink/test](/mnt/hdd1/ink-python/js_source/ink/test)

### 为什么是 P0

没有测试基线，整改只能靠肉眼对比，极易在后续修改中引入回退。

### 建议交付

- 建一批最小高价值测试集，优先覆盖：
  - render 实例契约
  - hooks state/effect 生命周期
  - input parser
  - useInput / usePaste
  - `<Static>`
  - `log_update`
- 测试命名尽量映射 JS 测试主题，便于对照

---

## P1：高优先级兼容项

## P1-1. 重写 `log_update`，补标准模式与增量模式

### 目标

对齐 JS 的 `log-update` 核心能力，尤其是标准重绘与 incremental 模式的分支语义。

### 当前问题

- Python `LogUpdate` 有 `incremental` 参数，但没有体现出 JS 那种两套行为模型。[log_update.py](/mnt/hdd1/ink-python/src/ink_python/log_update.py#L20)
- 缺少 cursor position、line diff、局部更新等能力。

### 建议交付

- 明确 standard mode / incremental mode 分支
- 支持最小粒度的行级 diff
- 正确处理 output 末尾换行
- 维护 cursor position 状态

### 对应测试

- 全量重绘
- 局部更新
- output 收缩/扩张
- cursor position 恢复

---

## P1-2. 升级 `Output` 渲染缓冲与 ANSI 处理

### 目标

缩小 Python 与 JS 在 ANSI、宽字符、裁剪、背景/边框渲染方面的差距。

### 当前问题

- Python `Output` 是二维字符串网格，对 ANSI 处理明显简化。[output.py](/mnt/hdd1/ink-python/src/ink_python/output.py#L181)
- JS 则有更完整的 styled chars、ANSI tokenizer、slice-ansi 处理链。

### 建议交付

- 明确单元格模型是“纯字符”还是“带样式 token”
- 修正 ANSI 截断与宽字符裁剪逻辑
- 为边框、背景、text style 提供更稳定的渲染拼接

### 对应测试

- ANSI 样式跨列截断
- 全角字符宽度
- 样式文本与边框同时存在
- 背景色覆盖区域正确

---

## P1-3. 对齐 `App` 根组件职责

### 目标

把 Python `App` 从“简单包裹层”提升为运行时管理入口。

### 当前问题

- JS `App` 负责 raw mode、cursor、stdin/stdout/stderr context、focus、paste、cleanup 等核心职责。[App.tsx](/mnt/hdd1/ink-python/js_source/ink/src/components/App.tsx#L26)
- Python `App` 目前能力明显简化。[app.py](/mnt/hdd1/ink-python/src/ink_python/components/app.py#L20)

### 建议交付

- 把 raw mode、cursor、paste mode、event emitter、focus manager 的协调逻辑收拢进 `App`
- 明确 context 注入边界
- 保证 unmount 时 cleanup 顺序稳定

### 对应测试

- 多 hooks 同时启用 raw mode 时引用计数正确
- unmount 时 raw mode/cursor/paste mode 正确恢复
- context 内部方法在 rerender 后稳定可用

---

## P1-4. 补齐 `usePaste`、`useFocus`、`useFocusManager` 的真实行为

### 目标

让这些 hooks 从“有 API 名称”升级为“有真实可验证行为”。

### 当前问题

- `usePaste` 当前未打通。
- `useFocus` / `useFocusManager` 虽有入口，但依赖底层输入与状态模型，行为很难和 JS 严格接近。

### 建议交付

- `usePaste`：事件订阅、raw mode、bracketed paste mode、cleanup
- `useFocus`：focusable 节点注册与状态查询
- `useFocusManager`：next/previous/focus(id)

### 对应测试

- paste 不应误流入普通 input
- 焦点切换顺序正确
- active/inactive hook 行为正确

---

## P1-5. 补齐 screen reader 通路

### 目标

让 Python 的 screen reader 支持从配置、context、hook 到 renderer 全链路打通。

### 当前问题

- Python renderer 虽有 screen reader 分支，但 `use_is_screen_reader_enabled()` 直接返回 `False`。[use_is_screen_reader_enabled.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_is_screen_reader_enabled.py#L10)

### 建议交付

- 让 hook 从 app/context 中读取真实状态
- 对齐 `aria-hidden` / `aria-label` 在 Text/Box 中的行为
- 增加 screen reader 模式测试

---

## P2：增强与完整度提升

## P2-1. kitty keyboard 支持

### 目标

补齐 JS Ink 在 kitty keyboard protocol 方面的能力。

### 当前问题

- Python 只有 `Options.kitty_keyboard` 字段，没有探测、启用、解析链路。[ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py#L69)

### 建议交付

- 加入 protocol 开启策略
- 支持 kitty modifiers
- 支持 eventType / super / hyper / capsLock / numLock

### 对应测试

- kitty CSI-u keypress
- kitty modifier keys
- kitty enhanced special keys

---

## P2-2. `patch_console` 与 stdout/stderr 恢复输出

### 目标

对齐 JS 中 console 输出与 Ink 输出之间的协调行为。

### 当前问题

- Python 没有同等级 console patch 机制。
- stderr/stdout 外部写入后的 UI 恢复行为也没有完整对齐。

### 建议交付

- 明确 console patch 范围
- 明确 teardown 期间 console 行为
- 增加 stdout/stderr 外部写入后的 UI 恢复逻辑

---

## P2-3. 完整布局/视觉边界兼容

### 目标

继续逼近 JS 在 layout 和视觉边界条件上的表现。

### 当前问题

- JS 测试覆盖了 overflow、gap、position、width/height、align-content、alternate-screen 边界等。
- Python 当前这类覆盖有限。

### 建议交付

- 补齐 layout 相关样式语义
- 对齐 overflow 和测量边界
- 加强宽高变化与 terminal resize 行为

---

## P2-4. 开发者体验与导出整理

### 目标

收敛 Python 暴露的 API 形态，减少“看起来有，但行为和 JS 不一致”的表面导出。

### 当前问题

- Python 顶层导出包含较多 React 风格内部构造和简化 hooks。
- 公开 API 与 JS Ink 的对外形态并不一致。

### 建议交付

- 区分“稳定公开 API”和“内部实现工具”
- 统一 snake_case / camelCase 对外策略
- 为缺失能力标记实验性或内部用途

---

## 推荐实施顺序

建议按下面顺序推进：

1. `P0-1` hooks 运行时模型
2. `P0-2` reconciler 增量更新
3. `P0-3` render / 实例契约
4. `P0-4` 输入系统骨架
5. `P0-5` parity 测试基线
6. `P1-1` log_update
7. `P1-2` Output / ANSI 处理
8. `P1-3` App 根组件职责
9. `P1-4` hooks 行为补齐
10. `P1-5` screen reader 通路
11. `P2-*` 增强项

---

## 每阶段完成标准

## P0 完成标准

- hooks 状态不再是全局单一模型
- reconciler 不再依赖整树重建
- `render()` 实例契约具备最小 parity 基础
- 输入系统具备 parser/event bus/raw mode 骨架
- 有一套可执行的 parity 测试基线

## P1 完成标准

- `log_update` 与 `Output` 足以支撑主要交互型 UI
- `App`、`usePaste`、`useFocus`、`useFocusManager` 行为可稳定测试
- screen reader 通路可用

## P2 完成标准

- kitty keyboard、console patch、复杂视觉边界和导出策略进一步逼近 JS
- 项目从“简化移植版”提升为“高兼容移植版”

---

## 最终建议

如果目标是“尽快把 `ink-python` 变成真正可比肩 JS Ink 的实现”，最重要的一点不是先补零散 API，而是先纠正底层运行时。

也就是说：

- **P0 不解决，P1/P2 的工作大概率会返工。**
- **越早建立 parity 测试，越能避免后续整改过程中不断回退。**

因此，实际执行时建议把人力优先集中在：

1. hooks 运行时
2. reconciler
3. render/实例契约
4. input parser 与事件系统
5. parity 测试

这五项是整个整改工作的地基。
