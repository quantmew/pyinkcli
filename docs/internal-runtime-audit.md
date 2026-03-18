# Internal Runtime Audit

本轮只审计这 4 个内部实现层：

- [\_component_runtime.py](/mnt/hdd1/ink-python/src/ink_python/_component_runtime.py)
- [hooks/\_runtime.py](/mnt/hdd1/ink-python/src/ink_python/hooks/_runtime.py)
- [\_suspense_runtime.py](/mnt/hdd1/ink-python/src/ink_python/_suspense_runtime.py)
- [\_yoga.py](/mnt/hdd1/ink-python/src/ink_python/_yoga.py)

目标不是看 facade，而是看这些内部层本身还承担了哪些和 `js_source/ink/src` 不一比一的职责。

## 总结

当前公开面已经基本收紧，剩余的非一比一问题主要集中在内部 runtime：

1. Python 自建了 React/JS 本应在仓库外或宿主库内承担的运行时。
2. Python 通过 facade + internal runtime 的拆法实现兼容，这不是 JS `src` 的原始结构。
3. 最偏离 JS 的不是文件名，而是职责来源：
   - `hooks/_runtime.py` 在 Python 里自建 hooks 调度。
   - `_suspense_runtime.py` 在 Python 里自建 Suspense 资源层。
   - `_component_runtime.py` 在 Python 里自建 element/component 记录。
   - `_yoga.py` 在 Python 里为 `quantmew/yoga-layout-python` 重新包装一整层 JS 风格 API。

## 1. `_component_runtime.py`

### 当前职责

- 定义内部 element 记录：`_Element`
- 定义 Python 侧“可渲染节点”：`RenderableNode`
- 负责 children 归一化、文本 coercion、props 归一化
- 提供 `createElement`
- 提供 `component` 装饰器
- 提供 `isElement`
- 提供 `renderComponent`
- 保留 class-style component 兼容层：`_Component`
- 保留 fragment 标记：`_Fragment`

### 对照 JS 的问题

- `js_source/ink/src` 里没有一个同级文件负责实现 `createElement` 和 hooks/component runtime。
- JS 这层能力来自 React，本仓库只消费 React，不自建 element record。
- `_Component`、`_Fragment`、`renderComponent` 都是 Python 侧自建概念，不是 JS Ink `src` 同级职责。
- `RenderableNode = Union["_Element", str, None]` 也是 Python 适配类型，不是 JS 的 ReactNode / JSX element 结构。

### 当前是否还需要继续缩面

结论：对外不需要再缩。

原因：

- facade [component.py](/mnt/hdd1/ink-python/src/ink_python/component.py) 已经只保留最小兼容面。
- `_component_runtime.py` 现在主要是内部实现，不再是公开 API 污染点。

### 还能继续往 parity 靠的点

- 把 `_Component` class-style 兼容进一步评估为“仅内部过渡层”，减少运行时实际依赖。
- 评估 `_Fragment` 是否真的需要保留，还是可以完全落到 reconciler 特判。
- 补一份“React-origin responsibility”注释，明确这是 Python 补齐层，不是 JS 原仓库同级模块。

## 2. `hooks/_runtime.py`

### 当前职责

- 保存所有 hook 实例状态：`RuntimeState`
- 保存单组件 hook 状态：`HookState`
- 实现：
  - `useState`
  - `useEffect`
  - `useRef`
  - `useMemo`
  - `useCallback`
  - `useReducer`
- 实现渲染周期内部控制：
  - `_reset_hook_state`
  - `_begin_component_render`
  - `_end_component_render`
  - `_finish_hook_state`
  - `_clear_hook_state`
  - `_set_rerender_callback`
  - `_request_rerender`
- 处理 effect cleanup、未挂载实例清理、pending effect flush

### 对照 JS 的问题

- 这是当前最明显的“不是一比一”的内部层。
- JS Ink `src` 直接使用 React hooks，不在仓库里实现 hooks runtime。
- Python 这里把 React 的调度、实例栈、effect flush、rerender 触发全部自己重建了一遍。
- `instance_id`、`instance_stack`、`visited_instances`、`pending_effects` 这些都是 Python runtime 专有结构。

### 功能风险

- `useEffect` 的执行时机只能近似 React，不可能天然等价。
- `useMemo` / `useCallback` / `useReducer` 的生命周期语义取决于 Python 这套实例标识模型。
- `__global__` fallback instance 也是 Python 特有行为，不对应 JS React 真实运行时。

### 当前是否还需要继续缩面

结论：不该再缩公开面，但应该明确这是“必要偏离点”。

原因：

- facade [hooks/state.py](/mnt/hdd1/ink-python/src/ink_python/hooks/state.py) 已是薄壳。
- 真正的问题不再是导出，而是这套内部 runtime 永远不可能和 JS React 实现一比一。

### 还能继续往 parity 靠的点

- 增加语义差异文档，明确哪些行为是“接近 React”，哪些不是。
- 增加行为级测试，重点覆盖：
  - effect cleanup 顺序
  - render-to-string 中 effect 执行语义
  - unmount cleanup
  - repeated render identity

## 3. `_suspense_runtime.py`

### 当前职责

- 定义 `SuspendSignal`
- 维护资源表 `_records`
- 维护全局锁 `_records_lock`
- 提供：
  - `readResource`
  - `preloadResource`
  - `peekResource`
  - `invalidateResource`
  - `resetResource`
  - `resetAllResources`
- 用后台线程执行 loader
- 在资源完成后调用 `_request_rerender`

### 对照 JS 的问题

- JS Ink 的 Suspense 语义建立在 React Suspense 之上，不存在同级 `_suspense_runtime.ts` 这种仓库内资源层。
- Python 这里是自建资源缓存 + 后台线程 + 异常信号机制。
- `SuspendSignal` 是 Python 运行时专用桥接物，不是 JS React 的原始概念实现方式。

### 功能风险

- 线程模型和 React concurrent/suspense 的调度模型不是一回事。
- `readResource` / `preloadResource` 的重入和取消语义，只能做到近似。
- `_request_rerender()` 是全局回调式触发，不是 React scheduler。

### 当前是否还需要继续缩面

结论：facade [suspense_runtime.py](/mnt/hdd1/ink-python/src/ink_python/suspense_runtime.py) 已经是终点。

接下来不该继续缩文件，而应该：

- 把它明确标记为 Python-specific runtime。
- 通过行为测试限定现有语义边界。

### 还能继续往 parity 靠的点

- 补充 `Suspense` 行为差异说明。
- 为 `concurrent-suspense` example 增加更细的行为级测试。
- 审计是否需要资源取消、重复 preload、错误恢复路径测试。

## 4. `_yoga.py`

### 当前职责

- 把 `quantmew/yoga-layout-python` 包装成 JS Ink 当前代码更容易消费的 API。
- 重新导出：
  - `YGDirection`
  - `YGFlexDirection`
  - `YGJustify`
  - `YGAlign`
  - `YGWrap`
  - `YGPositionType`
  - `YGDisplay`
  - `YGEdge`
  - `YGGutter`
- 再导出一组 JS 风格常量：
  - `DIRECTION_*`
  - `FLEX_DIRECTION_*`
  - `JUSTIFY_*`
  - `ALIGN_*`
  - `WRAP_*`
  - `POSITION_TYPE_*`
  - `DISPLAY_*`
  - `EDGE_*`
  - `GUTTER_*`
  - `UNDEFINED`
- 定义 `LayoutNode` 包装类
- 定义 `NodeWrapper` / `Node.create()`
- 定义 `Config`

### 对照 JS 的问题

- JS 直接消费 `yoga-layout`，不会在 Ink 仓库里自己重新包装 `Node` / enum / constant。
- Python 这里必须额外适配 `quantmew/yoga-layout-python`，这是技术上不可避免的偏离。
- `LayoutNode`、`NodeWrapper`、`Node = NodeWrapper` 都是 Python 适配层，不是 JS 原结构。

### 当前是否还需要继续缩面

结论：不建议继续缩。

原因：

- 这层是整个布局系统兼容 `yoga-layout-python` 的桥。
- 继续压缩只会让内部代码更难读，不会提升和 JS `ink/src` 的同构度。
- 本轮已经把 facade [yoga_compat.py](/mnt/hdd1/ink-python/src/ink_python/yoga_compat.py) 收成显式最小导出。

### 还能继续往 parity 靠的点

- 在文档里明确：这是“依赖适配层”，不是“JS 源码结构未翻译完整”。
- 如果未来 `quantmew/yoga-layout-python` API 更接近 JS `yoga-layout`，可以减少这一层包装厚度。

## 审计结论

这 4 个文件里，真正还“看起来不一比一”的原因，不再是公开面漂移，而是职责来源本身不同：

- `_component_runtime.py`：补 React element/component 层
- `hooks/_runtime.py`：补 React hooks/runtime 层
- `_suspense_runtime.py`：补 React Suspense resource 层
- `_yoga.py`：补 Python Yoga 依赖适配层

换句话说，当前剩下的差异是“宿主生态差异导致的必要内部 runtime”，不是“文件没翻对”。

## 下一步建议

如果继续推进，不建议再机械压缩这 4 个文件本身，而应该转成两条线：

1. 行为差异审计
   - 重点测 `hooks/_runtime.py` 和 `_suspense_runtime.py`
   - 目标是明确“和 React/JS Ink 哪些地方等价，哪些地方只是近似”

2. 依赖适配说明
   - 给 `_yoga.py` 和 `_component_runtime.py` 补一份“为什么必须存在”的说明
   - 避免后续把“必要适配层”误判成“未完成 parity”
