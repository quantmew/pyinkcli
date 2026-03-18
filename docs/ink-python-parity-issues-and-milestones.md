# ink-python Parity 任务拆解清单

## 用法说明

这份文档把前面的整改路线图继续细化成可执行任务，格式尽量贴近 issue / milestone 管理方式。

建议使用方式：

- 每个 `Milestone` 作为一个里程碑
- 每个 `Issue` 作为一个独立任务
- `Depends on` 表示依赖关系
- `Acceptance Criteria` 可直接作为验收标准

---

## Milestone 0：Parity 基线与架构纠偏

### 目标

建立后续 parity 改造的基础，避免继续在错误运行时模型上追加功能。

### 完成标准

- hooks 不再基于全局单一状态
- reconciler 不再依赖整树重建
- render/实例契约具备最小 parity 基础
- 输入系统有独立 parser/event bus 骨架
- Python 侧建立一套最小 parity 测试集

---

## Issue M0-1：重构 hooks 状态存储模型

### Priority

`P0`

### Problem

当前 hooks 状态建立在全局 `_current_state` 上，不具备组件级实例隔离能力。[state.py](/mnt/hdd1/ink-python/src/ink_python/hooks/state.py#L27)

### Scope

- 重构 `src/ink_python/hooks/state.py`
- 为组件实例引入独立 hook state
- 明确 render 阶段索引推进逻辑
- 支持 effect cleanup 生命周期

### Out of Scope

- 并发 hooks 语义
- Suspense 语义

### Depends on

- 无

### Acceptance Criteria

- 两个组件同时使用 `useState()` 时状态互不串扰
- rerender 后 hook 顺序稳定
- `useEffect()` 在依赖变化时重新执行
- `useEffect()` cleanup 在重新执行和卸载时均可触发
- `useRef/useMemo/useCallback` 可随组件实例独立工作

### Suggested Files

- [state.py](/mnt/hdd1/ink-python/src/ink_python/hooks/state.py)
- [reconciler.py](/mnt/hdd1/ink-python/src/ink_python/reconciler.py)

---

## Issue M0-2：为组件实例建立 hooks 上下文绑定机制

### Priority

`P0`

### Problem

即使重构了 hook state，如果没有组件实例级上下文绑定，函数组件执行时仍然无法正确读写自己的 hook 槽位。

### Scope

- 在函数组件渲染时建立“当前组件实例”上下文
- 在 render 结束后正确清理上下文
- 为 hooks 提供内部访问当前实例 state 的入口

### Depends on

- `M0-1`

### Acceptance Criteria

- 嵌套函数组件各自维护独立 hook 状态
- 父组件 rerender 不会破坏子组件已有 state
- 多个兄弟组件 hooks 顺序不互相污染

---

## Issue M0-3：重构 reconciler，移除“整树清空后重建”路径

### Priority

`P0`

### Problem

当前 `update_container()` 每次都会先删光 children 再重新建树。[reconciler.py](/mnt/hdd1/ink-python/src/ink_python/reconciler.py#L75)

### Scope

- 设计最小增量 reconciler 机制
- 支持 host node 的更新而非销毁重建
- 保持节点 identity 稳定
- 支持文本节点更新

### Depends on

- `M0-1`
- `M0-2`

### Acceptance Criteria

- props 更新不会导致整棵树被重建
- 文本更新只影响对应文本节点
- 未变化的子树保留 identity
- `<Static>` 节点在普通 rerender 中不被错误重建

### Suggested Files

- [reconciler.py](/mnt/hdd1/ink-python/src/ink_python/reconciler.py)
- [dom.py](/mnt/hdd1/ink-python/src/ink_python/dom.py)

---

## Issue M0-4：补齐 reconciler 的 child 插入、删除、重排能力

### Priority

`P0`

### Problem

没有 child diff/reorder，很多 JS Ink 场景都无法正确对齐。

### Scope

- 支持 append / remove / insert before
- 支持 keyed 或稳定顺序下的 child 重排
- 为后续 focus/static/layout 行为保留稳定节点身份

### Depends on

- `M0-3`

### Acceptance Criteria

- child list 增删时父节点保持稳定
- child reorder 不会丢失未变化节点状态
- 重排后的输出顺序正确

---

## Issue M0-5：对齐 render 实例契约

### Priority

`P0`

### Problem

Python `render()` 直接返回 `Ink` 实例，缺少 JS `Instance` 语义中的 `waitUntilRenderFlush`、`cleanup` 等能力。[ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py#L683) [render.ts](/mnt/hdd1/ink-python/js_source/ink/src/render.ts#L138)

### Scope

- 定义 Python 侧实例契约
- 增加 `wait_until_render_flush`
- 增加 `cleanup`
- 明确 `rerender` 语义

### Depends on

- `M0-3`

### Acceptance Criteria

- rerender 后可等待输出 flush
- cleanup 后可在同一输出流上创建新实例
- unmount 与 wait_until_exit 的行为边界明确
- clear 在 interactive 与 non-interactive 下行为可测

### Suggested Files

- [ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py)
- [__init__.py](/mnt/hdd1/ink-python/src/ink_python/__init__.py)

---

## Issue M0-6：建立输入 parser 骨架

### Priority

`P0`

### Problem

当前输入解析只覆盖简化 ANSI 序列，没有 JS 那套 `input-parser` 的 chunk 级处理能力。[use_input.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_input.py#L119)

### Scope

- 新增独立输入 parser 模块
- 处理 escape sequence chunk 边界
- 区分 printable input / control keys / paste
- 为后续 event bus 提供结构化输入事件

### Depends on

- 无

### Acceptance Criteria

- 普通字符输入正确
- `Escape`、`Tab`、`Delete`、`Backspace`、箭头键解析正确
- 分块到达的 escape sequence 不会误判
- 连续 delete/backspace 不会因 chunk 合并而损坏状态

### Suggested Files

- 新增 `src/ink_python/input_parser.py`
- [use_input.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_input.py)

---

## Issue M0-7：建立 stdin 事件总线与 raw mode 协调层

### Priority

`P0`

### Problem

当前 `useInput`、`usePaste`、`useFocus` 无法共享统一输入基础设施。

### Scope

- 在 `StdinHandle` 或 `App` 层建立统一事件分发
- 支持内部事件：
  - `input`
  - `paste`
- 集中管理 raw mode 引用计数

### Depends on

- `M0-6`

### Acceptance Criteria

- 多个 hook 可共享同一输入事件源
- raw mode 只在需要时开启
- 最后一个依赖 raw mode 的 hook 卸载后正确关闭 raw mode

### Suggested Files

- [use_stdin.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_stdin.py)
- [components/app.py](/mnt/hdd1/ink-python/src/ink_python/components/app.py)

---

## Issue M0-8：补齐 parity 最小测试基线

### Priority

`P0`

### Problem

当前 Python 测试无法覆盖大多数关键行为差异。

### Scope

- 新增一批最小高价值测试
- 覆盖：
  - hooks state/effect
  - render 实例契约
  - input parser
  - `useInput`
  - `<Static>`
  - basic log update

### Depends on

- `M0-1`
- `M0-3`
- `M0-5`
- `M0-6`

### Acceptance Criteria

- 测试文件结构能映射到主要 JS 测试主题
- 新增测试可稳定复现当前修复目标
- 后续 P1/P2 工作可以继续在这套测试上扩展

---

## Milestone 1：关键功能对齐

### 目标

在 P0 骨架完成后，补齐影响大多数 Ink 交互场景的关键功能。

### 完成标准

- `log_update` 和 `Output` 足以支撑交互型 UI
- `App` 具备核心 runtime 协调职责
- `usePaste` / `useFocus` / `useFocusManager` 具备真实行为
- screen reader 通路打通

---

## Issue M1-1：重写 `log_update`，区分 standard / incremental 模式

### Priority

`P1`

### Problem

Python `log_update` 只有表面参数，没有 JS 那种标准模式和增量模式的核心差异。[log_update.py](/mnt/hdd1/ink-python/src/ink_python/log_update.py#L20)

### Scope

- 明确 standard mode
- 明确 incremental mode
- 支持最小行级 diff
- 正确处理尾换行与 cursor position

### Depends on

- `M0-5`

### Acceptance Criteria

- standard mode 能稳定整块重绘
- incremental mode 能仅更新变更行
- output 收缩和扩张都能正确清屏/局部更新
- cursor position 恢复逻辑可测试

### Suggested Files

- [log_update.py](/mnt/hdd1/ink-python/src/ink_python/log_update.py)
- [ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py)

---

## Issue M1-2：升级 `Output` 模型，补齐 ANSI 与宽字符处理

### Priority

`P1`

### Problem

当前 `Output` 只是二维字符串网格，对 ANSI 和复杂裁剪场景支持不足。[output.py](/mnt/hdd1/ink-python/src/ink_python/output.py#L181)

### Scope

- 重构单元格模型
- 支持 ANSI 样式安全裁剪
- 补齐宽字符与列宽处理
- 稳定背景、边框、文本样式叠加

### Depends on

- `M1-1`

### Acceptance Criteria

- 带 ANSI 的字符串切片不破坏样式闭合
- 全角字符和混合宽度字符渲染正确
- border/background/text style 混合渲染正确

---

## Issue M1-3：扩展 `App` 根组件职责

### Priority

`P1`

### Problem

Python `App` 目前只是简化包裹层，无法承担 JS `App` 的 runtime 协调职责。[app.py](/mnt/hdd1/ink-python/src/ink_python/components/app.py#L20)

### Scope

- 收拢 stdin/stdout/stderr context 管理
- 集中管理 raw mode、cursor、paste mode、cleanup 顺序
- 提供给 hooks 的稳定上下文能力

### Depends on

- `M0-7`

### Acceptance Criteria

- raw mode 不再由多个 hooks 各自直接抢占
- unmount 时 cursor/raw mode/paste mode 都能稳定恢复
- rerender 不会破坏 App 内部上下文

---

## Issue M1-4：真正实现 `usePaste`

### Priority

`P1`

### Problem

当前 `usePaste` 实际未打通。

### Scope

- 打通 bracketed paste mode
- 建立 `paste` 事件订阅与取消订阅
- 与 `useInput` 分流

### Depends on

- `M0-6`
- `M0-7`
- `M1-3`

### Acceptance Criteria

- paste 文本不会逐字符误流入 `useInput`
- paste handler 可以启停
- 组件卸载时 paste mode 正确清理

### Suggested Files

- [use_paste.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_paste.py)
- [use_stdin.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_stdin.py)

---

## Issue M1-5：补齐 `useFocus` / `useFocusManager`

### Priority

`P1`

### Problem

当前 focus hooks 有入口，但行为层与 JS 不等价。

### Scope

- 建立 focusable 节点注册机制
- 支持 `focus_next`
- 支持 `focus_previous`
- 支持按 id 聚焦

### Depends on

- `M0-1`
- `M0-3`
- `M0-7`

### Acceptance Criteria

- 多个 focusable 组件可稳定轮转焦点
- `focus(id)` 可命中目标节点
- inactive/focused 状态在 rerender 后不丢失

---

## Issue M1-6：打通 screen reader 能力

### Priority

`P1`

### Problem

Python renderer 虽有 screen reader 分支，但 hook 层未打通，当前 `use_is_screen_reader_enabled()` 直接返回 `False`。[use_is_screen_reader_enabled.py](/mnt/hdd1/ink-python/src/ink_python/hooks/use_is_screen_reader_enabled.py#L10)

### Scope

- 让 hook 从 app/context 获取真实状态
- 校正 `aria-hidden`、`aria-label` 行为
- 增加 screen reader 相关测试

### Depends on

- `M1-3`

### Acceptance Criteria

- 设置 screen reader 模式后 hook 返回真实值
- `aria-hidden` 节点不会出现在 screen reader 输出中
- `aria-label` 可覆盖默认朗读内容

---

## Issue M1-7：扩充关键行为测试集

### Priority

`P1`

### Problem

P1 交付需要对应测试，否则仍然难以稳定收敛。

### Scope

- `log_update`
- `Output`
- `usePaste`
- `useFocus`
- screen reader
- alternate screen 关键路径

### Depends on

- `M1-1`
- `M1-2`
- `M1-4`
- `M1-5`
- `M1-6`

### Acceptance Criteria

- 每个 P1 功能点至少有一组正向测试和一组边界测试

---

## Milestone 2：高级能力与完整度提升

### 目标

继续向 JS Ink 靠近，补齐高级输入能力、stdout/stderr 协调、视觉与布局边界兼容。

### 完成标准

- kitty keyboard 具备可用实现
- console patch / 恢复输出逻辑具备明确行为
- layout/视觉边界兼容性显著提升
- 导出与文档更清晰地区分稳定能力和实验能力

---

## Issue M2-1：实现 kitty keyboard protocol 支持

### Priority

`P2`

### Problem

Python 只有 `kitty_keyboard` 选项字段，没有真正实现链路。[ink.py](/mnt/hdd1/ink-python/src/ink_python/ink.py#L69)

### Scope

- 增加 protocol 探测/启用策略
- 解析 kitty modifiers
- 支持 eventType、super、hyper、capsLock、numLock

### Depends on

- `M0-6`
- `M0-7`

### Acceptance Criteria

- kitty CSI-u 输入可正确解析
- kitty 修饰键可传递到 `useInput`
- 不支持 kitty 的环境下不会破坏普通输入

---

## Issue M2-2：实现 `patch_console`

### Priority

`P2`

### Problem

Python 缺少 JS Ink 中 console 输出与 UI 输出之间的协调能力。

### Scope

- patch `print`/console 风格输出与 Ink 输出的相互关系
- 输出后恢复 UI
- 明确 teardown 期间行为

### Depends on

- `M1-1`
- `M1-3`

### Acceptance Criteria

- 运行中外部 stdout/stderr 输出后 UI 可恢复
- teardown 阶段行为符合预期且有文档说明

---

## Issue M2-3：补齐 `write-synchronized` 语义

### Priority

`P2`

### Problem

Python 缺少 JS `write-synchronized` 一类能力，复杂终端环境下输出一致性可能不足。

### Scope

- 评估是否需要专门模块
- 在 interactive 场景下提供同步写出控制
- 与 `log_update` 集成

### Depends on

- `M1-1`

### Acceptance Criteria

- 交互式重绘期间不会因写出竞争造成明显破屏

---

## Issue M2-4：补齐布局与视觉边界行为

### Priority

`P2`

### Problem

JS 侧在 overflow、gap、position、width/height、alternate-screen 边界上测试更完整，Python 仍有差距。

### Scope

- 补齐 layout 样式边界行为
- 加强 resize 场景处理
- 对齐 overflow 和尺寸测量细节

### Depends on

- `M0-3`
- `M1-2`

### Acceptance Criteria

- 关键布局属性在组合场景下输出稳定
- resize 后布局与输出不混乱
- overflow 裁剪行为有测试覆盖

---

## Issue M2-5：整理公开导出与稳定性标记

### Priority

`P2`

### Problem

当前 Python 顶层导出包含较多“看起来像 React/Ink，但语义未完全对齐”的能力，容易误导使用者。

### Scope

- 区分稳定 API 和内部实现 API
- 收敛顶层导出
- 为未完成能力增加实验性说明
- 统一 snake_case / camelCase 策略

### Depends on

- `M0-5`
- `M1-*`

### Acceptance Criteria

- README 与顶层导出契约一致
- 实验性能力不会被误认为已完成 parity

---

## 建议里程碑顺序

### Milestone 0

- `M0-1`
- `M0-2`
- `M0-3`
- `M0-4`
- `M0-5`
- `M0-6`
- `M0-7`
- `M0-8`

### Milestone 1

- `M1-1`
- `M1-2`
- `M1-3`
- `M1-4`
- `M1-5`
- `M1-6`
- `M1-7`

### Milestone 2

- `M2-1`
- `M2-2`
- `M2-3`
- `M2-4`
- `M2-5`

---

## 推荐拆分方式

如果要直接在项目管理工具中建任务，建议这样拆：

- `Milestone 0`：架构纠偏
- `Milestone 1`：核心兼容
- `Milestone 2`：高级能力与收尾

每个 milestone 下：

- 1 个 architecture issue
- 2 到 4 个 feature issue
- 1 个 test issue
- 1 个 docs / export cleanup issue

---

## 最终建议

执行时应尽量避免两种做法：

1. 在没有重构 hooks / reconciler 的情况下，继续给 Python 版追加表层 hooks/API
2. 在没有 parity 测试的情况下，一边重构 runtime 一边盲补特性

更稳妥的推进方式是：

1. 先完成 `Milestone 0`
2. 以测试驱动方式推进 `Milestone 1`
3. 最后处理 `Milestone 2` 的高级能力和文档收尾

这样能把返工风险降到最低。
