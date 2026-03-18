# Runtime Behavior Audit

本轮从“结构收缩”切到“行为差异审计”，重点看：

- [hooks/\_runtime.py](/mnt/hdd1/ink-python/src/ink_python/hooks/_runtime.py)
- [\_suspense_runtime.py](/mnt/hdd1/ink-python/src/ink_python/_suspense_runtime.py)

对照基准：

- `js_source/ink/src` 内可确认的文档和实现注释
- 当前 Python 运行时的实测行为

## 1. `hooks/_runtime.py`

### 已确认和 JS Ink 文档一致的点

- `renderToString()` 中，`useEffect` 会执行。
- `useEffect` 内触发的 state update 不会影响 `renderToString()` 返回值。

这个结论直接对应 [render-to-string.ts](/mnt/hdd1/ink-python/js_source/ink/src/render-to-string.ts) 里的说明：

- `useEffect callbacks will execute during rendering`
- `state updates they trigger will not affect the returned output`

Python 实测结果也一致：

- 初次 render 输出仍然是初始 state
- effect 已执行
- effect 里的 `setState()` 不会改变本次返回字符串

### 已确认的 Python 运行时语义

- `useEffect` 在 deps 不变时不会重复执行。
- 当 deps 变化时，会先执行上一次 cleanup，再执行新 effect。
- unmount 时会执行 cleanup。
- `setState()` 每次调用都会直接触发 rerender callback。
- 不同嵌套组件实例只要 `instance_id` 不同，hook state 就彼此隔离。
- 某个组件实例在一次 render cycle 中消失后，再次以同一 `instance_id` 挂回时，state 会从初始值重新开始。

### 与 React/JS Ink 的潜在差异

- Python 没有 React scheduler。
- Python 没有 `useLayoutEffect` / `useInsertionEffect` 的独立阶段模型。
- effect flush、rerender 触发、组件实例标识，都依赖 Python 自己的 `instance_id` 和全局 runtime 状态。
- `setState()` 连续调用时，目前是“每次更新都请求一次 rerender”，这更接近简单回调式 runtime，不是 React 的批处理模型。

### 当前判断

- `renderToString()` 上最关键的 `useEffect` 语义已经和 JS 文档对齐。
- hooks 生命周期的更细粒度语义，目前应标记为“近似 React”，不是“已证明完全等价”。

## 2. `_suspense_runtime.py`

### 已确认的 Python 运行时语义

- 对同一个 pending resource key，`readResource()` 只会启动一次 loader。
- 后续在 pending 期间再次 `readResource()`，会继续抛 `SuspendSignal`，不会重复启动 loader。
- resource resolve 后，`peekResource()` 可读到缓存值。
- resource reject 后，错误会被缓存；后续再次 `readResource()` 会重复抛同一个错误，直到 `resetResource()`。
- loader 完成后会调用 `_request_rerender()` 触发重新渲染。
- 多个 Suspense boundary 可以分阶段 reveal；先 resolve 的 boundary 会先从 fallback 切到真实内容。
- `resetResource()` 后，已 resolve 的 boundary 会重新进入 fallback，然后再次 resolve。

### 与 React/JS Ink 的潜在差异

- Python 用线程 + 全局资源表 + `SuspendSignal` 近似 Suspense。
- React Suspense 不是这个线程模型，也不是这个异常桥接实现。
- 取消、并发优先级、transition 协调，这一层都没有 React scheduler 语义。

### 当前判断

- 资源缓存和“单次加载 + resolve/reject 后重渲染”的核心行为已经稳定。
- 但这仍然只能算“Python 版 Suspense 近似实现”，不能视为 React Suspense 的一比一复刻。

## 3. 本轮新增验证

新增了这些行为级测试：

- [test_hooks.py](/mnt/hdd1/ink-python/tests/test_hooks.py)
  - deps 变化时 cleanup 顺序
  - 多次 `setState()` 的 rerender 请求语义
  - 嵌套实例 `instance_id` 隔离
  - unmount/remount 后 state 重置
- [test_runtime_behavior_audit.py](/mnt/hdd1/ink-python/tests/test_runtime_behavior_audit.py)
  - `renderToString()` 的 `useEffect` 语义
  - Suspense resource 单次 loader 启动语义
  - Suspense resource reject 缓存语义
  - 多 boundary staged fallback/reveal
  - resource reset 后 fallback -> resolve 的输出稳定性

## 4. 下一步建议

接下来最值得补的是两类测试：

1. hooks 更细语义
   - 嵌套组件 instance identity
   - unmount/re-mount 后 memo/ref 行为
   - 连续 state update 是否需要模拟更接近 React 的批处理

2. Suspense 更细语义
   - 多 boundary 并发加载
   - fallback 切换时序
   - resolve/reject/reset 后的输出稳定性
