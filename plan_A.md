# plan_A

目标：`pyinkcli` 的更新/调度/flush 语义尽量严格对齐 `js_source/react`、`js_source/react-reconciler`、`js_source/ink`，只做上游已有的优化路径，不引入额外的宿主层捷径。

## 范围约束

- 不做 `needs_layout` / `layout_dirty` / subtree layout / 双 root / imperative prompt 之类上游没有的方案。
- `resetAfterCommit -> onComputeLayout -> host render` 这一层先保持与 `js_source/ink/src/reconciler.ts` 一致。
- 优化重点放在：
  - hook update queue
  - lane / event priority
  - scheduleUpdateOnFiber 风格的调度入口
  - eager bailout
  - batchedUpdates / discreteUpdates / flushSync 语义

## 必改文件

### 1. `/mnt/hdd1/ink-python/src/pyinkcli/hooks/_runtime.py`

职责调整：

- 从“全局 hooks runtime + 全局 rerender callback”收缩为“hooks 执行期辅助层”。
- 不再直接承担 state 更新调度。

必须改动：

- 删除或废弃以下 root 级调度逻辑：
  - `_rerender_callback`
  - `_request_rerender()`
  - `_scheduled_rerender_loop()`
  - `_schedule_scheduled_rerender()`
  - `_flush_scheduled_rerender()`
  - `rerender_pending`
  - `scheduled_rerender`
  - `after_batch_callbacks`
- `useState()` setter 不再直接写 `state.states[index]` 后调用 `_request_rerender()`。
- `useState()` / 后续 `useReducer()` 要改成：
  - 通过当前 fiber / current hook queue 生成 update
  - 交给 reconciler 的 `dispatchSetState` 风格逻辑
- render-phase update 的处理方式要对齐上游 fallback 语义，而不是直接全局排队 rerender。

保留项：

- 当前组件调用期间的 hook 顺序管理。
- effect/ref/memo 的基础记录结构，但存储位置要逐步向 fiber hook 链表模型迁移。

风险：

- 这是最大改动点，现有 hook 状态索引模型与 React 的 `Hook.next` 链式结构不一致，后续会牵引多文件联动。

### 2. `/mnt/hdd1/ink-python/src/pyinkcli/hooks/state.py`

职责调整：

- 只做 public compatibility export，不再暴露 runtime 私有 rerender 机制。

必须改动：

- 移除对 `_consume_pending_rerender_priority`、`_set_rerender_callback` 这类过时接口的转发。
- 对外只保留与 React hooks 表面一致的 hook API。

### 3. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactEventPriorities.py`

职责调整：

- 从字符串优先级薄封装，升级为更接近上游 `ReactEventPriorities.js` 的 lane/event priority 映射层。

必须改动：

- 用数值型 lane / event priority 取代：
  - `"default"`
  - `"discrete"`
  - `"render_phase"`
- 增加与上游对应的常量：
  - `NoEventPriority`
  - `DiscreteEventPriority`
  - `DefaultEventPriority`
  - 如需要可加 `ContinuousEventPriority`、`IdleEventPriority`
- 增加辅助函数：
  - `eventPriorityToLane`
  - `lanesToEventPriority`
  - `higherEventPriority`
  - `lowerEventPriority`

说明：

- 如果不先把这里改掉，后面的 work loop 无法严格对齐。

### 4. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberWorkLoop.py`

职责调整：

- 从“container 级 rerender while-loop”改为更接近上游 work loop 的更新调度中心。

必须改动：

- 删除或重写以下非上游结构：
  - `requestRerender()`
  - `drainPendingRerenders()`
  - `rerender_requested`
  - `rerender_running`
  - `pending_rerender_priority`
- 新增并对齐上游职责：
  - `requestUpdateLane(fiber)`
  - `scheduleUpdateOnFiber(root, fiber, lane)`
  - `batchedUpdates(...)`
  - `discreteUpdates(...)`
  - `flushSyncFromReconciler(...)`
- 把“调当前 root component 重跑”的逻辑改成“标 root pending lane，再由 reconciler/work loop 决定如何刷新”。

必须保留的宿主边界：

- commit 后仍通过 host config 请求 render。
- 不在这一层引入 layout shortcut。

### 5. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberRoot.py`

职责调整：

- 从简单 container rerender 状态，升级为 root pending lanes / finished lanes / render bookkeeping 容器。

必须改动：

- 删除：
  - `rerender_requested`
  - `rerender_running`
  - `pending_rerender_priority`
  - `current_render_priority`
- 新增：
  - `pending_lanes`
  - `suspended_lanes`
  - `finished_lanes`
  - `callback_node`
  - `callback_priority`
  - `current` / `finished_work` 一类更接近 FiberRoot 的字段

说明：

- 只要 root 还停留在“请求 rerender 的布尔状态机”，就无法对齐 React。

### 6. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberReconciler.py`

职责调整：

- 从 runtime helper 汇总器，改为真正对接 reconciler work loop 的 facade。

必须改动：

- `batchedUpdates()`、`discreteUpdates()` 不能再只是 `_runtime.py` 的包装。
- 补充与上游 facade 对齐的导出入口：
  - `flushSyncFromReconciler`
  - 需要的话补 `flushSyncWork`
- 去掉 `consumePendingRerenderPriority()` 这一类仅服务旧模型的接口。

### 7. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberReconcilerWorkLoop.py`

职责调整：

- 当前只是旧 `requestRerender` 体系的壳，需要对齐到新的 work loop facade。

必须改动：

- 删除对：
  - `_request_rerender`
  - `_drain_pending_rerenders`
  的依赖
- 改为透传：
  - `batched_updates`
  - `discrete_updates`
  - `flush_sync_from_reconciler`
  - `schedule_update_on_fiber`
  - `request_update_lane`

### 8. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/reconciler.py`

职责调整：

- 需要承接 fiber、root、host config、work loop 的新对齐关系。

必须改动：

- 当前 reconciler 对 hooks/runtime 的耦合要减少。
- 增加：
  - 当前执行 fiber
  - 当前 hook
  - 当前 render lanes
  - root 调度入口
- 把 hook dispatch 和 fiber/root 调度串起来。

### 9. `/mnt/hdd1/ink-python/src/pyinkcli/ink.py`

职责调整：

- 保持 host renderer 行为接近 `js_source/ink/src/ink.tsx`，但要接入新的 flush 语义。

必须改动：

- 移除对 `_set_rerender_callback(self._rerender)` 这类旧 runtime 回调模式的依赖。
- `request_render` 的来源改成 reconciler commit/work loop，而不是 hooks runtime。
- 明确区分：
  - `onRender`
  - `onImmediateRender`
  - `flushSync` / discrete update 造成的同步提交

说明：

- 这里不应该承担新的调度逻辑，只负责 host render 节流和终端输出。

### 10. `/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_input.py`

职责调整：

- 保持 `discreteUpdates` 入口，但语义要跟新的 reconciler 实现对齐。

必须改动：

- 校验 `discreteUpdates(lambda: ...)` 最终只是设置 update priority 并触发标准 update queue，而不是走旧 root rerender 快捷路径。

### 11. `/mnt/hdd1/ink-python/src/pyinkcli/hooks/use_paste.py`

职责调整：

- 同 `use_input.py`，保证输入事件更新走统一 discrete 优先级路径。

### 12. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberCommitWork.py`

职责调整：

- 保持 host commit 边界与 `js_source/ink/src/reconciler.ts` 对齐。

必须改动：

- 不再依赖 `container.current_render_priority` 这种旧 root 状态。
- render 请求优先级改从 lane / event priority 派生。
- `resetAfterCommit()` 的宿主行为保持现状，不在这里加自定义 shortcut。

### 13. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberContainerUpdate.py`

职责调整：

- 保持与 host container update 相容，但避免承担旧模型里多余的 rerender 调度责任。

必须改动：

- 清理任何直接走 `request_rerender(container, priority=...)` 的旧调用点。
- updateContainer / submitContainer 应该更像“创建 update 并 enqueue 到 root”。

## 可删文件

### 1. `/mnt/hdd1/ink-python/src/pyinkcli/hooks/state.py`

条件删除：

- 如果只是旧 runtime 私有接口的兼容层，没有其他 public 价值，可以删。
- 如果外部已有 import 依赖，则保留文件名，但内容降为薄 re-export。

### 2. `_runtime.py` 内以下逻辑块可删

- `_scheduled_rerender_loop`
- `_schedule_scheduled_rerender`
- `_flush_scheduled_rerender`
- `_set_rerender_callback`
- 旧 `rerender_pending` / `scheduled_rerender` 相关状态

说明：

- 这些更适合视为“可删逻辑”，即使文件本身不删。

### 3. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberWorkLoop.py` 中旧 rerender API

可删符号：

- `requestRerender`
- `drainPendingRerenders`
- `priorityRank` 如果 lane 化后不再需要字符串 rank

### 4. `/mnt/hdd1/ink-python/src/pyinkcli/packages/react_reconciler/ReactFiberReconciler.py` 中旧接口

可删符号：

- `consumePendingRerenderPriority`

## 需要新增的数据结构

### 1. Hook 链表结构

目标：对齐上游 `Hook`。

建议字段：

- `memoized_state`
- `base_state`
- `base_queue`
- `queue`
- `next`

用途：

- 替代当前 `HookState.states[]` 的纯索引存储模型。

### 2. Hook Update 结构

目标：对齐上游 `Update<S, A>`。

建议字段：

- `lane`
- `action`
- `has_eager_state`
- `eager_state`
- `next`

可选：

- `revert_lane`
- transition 相关字段，按当前支持范围决定

### 3. Hook UpdateQueue 结构

目标：对齐上游 `UpdateQueue<S, A>`。

建议字段：

- `pending`
- `lanes`
- `dispatch`
- `last_rendered_reducer`
- `last_rendered_state`

用途：

- 支持 eager bailout
- 支持 queue 合并和 render 阶段重放

### 4. FiberRoot 级 lane 状态

建议字段：

- `pending_lanes`
- `suspended_lanes`
- `pinged_lanes`
- `finished_lanes`
- `callback_priority`
- `callback_node`

用途：

- 对齐 root 调度
- 支持后续并发/transition 语义延展

### 5. ExecutionContext

建议定义：

- `NoContext`
- `BatchedContext`
- `RenderContext`
- `CommitContext`

用途：

- 对齐 `batchedUpdates` / `discreteUpdates` / `flushSyncFromReconciler`

### 6. Current update priority 存储

建议位置：

- 新增一个类似 shared internals 的模块，承载：
  - `current_update_priority`
  - 当前 transition

用途：

- 不再把 priority 只挂在 `_runtime` 里。

### 7. Render-phase update 暂存结构

用途：

- 对齐 React render-phase update fallback 语义。

至少需要：

- 标记当前是否处于 render context
- 当前 render lanes
- render-phase updates pending queue

## 需要补的兼容测试点

### A. Hooks 基础语义

- `useState` 初始值只初始化一次。
- `setState` 函数 identity 在多次 render 间稳定。
- `Object.is` 语义等价更新不触发额外 render。
- render-phase update 行为与当前目标语义一致，不出现死循环或漏更新。

### B. eager bailout

- queue 为空且新 state 与旧 state 相同，update 被 eager bailout。
- eager bailout 后，如果组件因其他原因重新 render，queue 语义仍正确。

### C. batchedUpdates

- 同一批次多个更新合并提交。
- 嵌套 `batchedUpdates` 行为正确。
- 批次结束后 flush 时机与目标模式一致。

### D. discreteUpdates

- 输入事件中 state 更新被标记为离散优先级。
- 离散更新优先于 default update。
- 离散更新不会绕开标准 hook queue / fiber 调度。

### E. flushSyncFromReconciler

- `flushSync` 可同步冲刷当前批次的同步更新。
- render/commit 过程中非法调用时行为与目标策略一致。
- `flushSync` 不错误地吞掉被 batch 的其他异步工作。

### F. Root 调度

- 一个 root 多次 update 会正确合并 pending lanes。
- 调度中再次 schedule update，不会退化为旧的“全局 rerender callback”。
- render phase、commit phase、passive phase 期间 update 的记录和后续处理正确。

### G. Host 行为对齐 Ink

- commit 后仍触发 `resetAfterCommit -> onComputeLayout -> onRender/onImmediateRender`。
- `Static` 节点仍保持 immediate render 逃生口语义。
- throttle 仍只发生在 host render 层，不污染 update queue 语义。

### H. 输入链路

- `use_input` 的键盘输入更新仍通过 `discreteUpdates`。
- 高频输入时不丢字符、不乱序。
- 输入处理中多次 state 更新具备正确 batching 语义。

### I. 回归测试

- 现有 `useEffect`、`useMemo`、`useRef` 不因 hooks 存储结构迁移而失效。
- 现有 suspense / transition 兼容层如果保留，需要至少保证行为不比当前更差。
- DevTools / inspection 相关路径不会因为 queue/fiber 数据结构变化直接崩。

## 推荐实施顺序

1. 先定义 lane / execution context / update queue 基础数据结构。
2. 重做 `ReactEventPriorities.py`、`ReactFiberRoot.py`、`ReactFiberWorkLoop.py`。
3. 把 `useState` 从 `_runtime.py` 直接写值，迁到 hook queue + scheduleUpdateOnFiber。
4. 补 eager bailout。
5. 接回 `ink.py` 的 host render/flush 路径。
6. 最后清理旧 rerender callback/thread 模型和冗余兼容层。

## 验收标准

- `pyinkcli` 不再依赖“全局 rerender callback + container.rerender_requested/running”作为核心更新模型。
- hook state 更新路径结构上接近：
  - dispatch
  - requestUpdateLane
  - enqueue update
  - scheduleUpdateOnFiber
  - commit
- host config 仍与 `js_source/ink` 的 commit/layout/render 边界保持一致。
- 本轮不引入任何上游没有的宿主层 shortcut。
