# Renderer/Reconciler Cache Parity Table

| Cache Layer | JS React / Reconciler | Current pyinkcli Status | Gap | Recommended Alignment |
| --- | --- | --- | --- | --- |
| Fiber double buffering | `current` / `workInProgress` fiber pair reused across renders | Partial | Python has some `alternate` usage, but not full upstream-style fiber lifecycle coverage | Strengthen `current` vs `workInProgress` ownership and make all render phases flow through it consistently |
| Props/state memoization | `memoizedProps`, `memoizedState`, update queues drive bailout | Partial | Present in places, but bailout semantics are not yet comprehensive | Expand begin-work bailout checks to use memoized props/state more like upstream |
| Child work caching | `childLanes` lets parent know whether subtree has pending work | Missing | Python tracks pending work more coarsely; subtree-level cached work visibility is weak | Add `childLanes`-style propagation so unchanged subtrees can skip work |
| Lane-based scheduling cache | `lanes`, `pendingLanes`, `suspendedLanes`, `pingedLanes`, `expiredLanes` | Partial | Python has lane helpers and root pending/suspended state, but not the full lane graph/cascade | Continue moving scheduling decisions to lane fields instead of ad hoc booleans |
| Context dependency cache | Fibers record context dependencies and re-render only when relevant context changes | Missing | Python can read context, but dependency tracking is not modeled like upstream | Add context dependency recording on fibers and use it in bailout decisions |
| Hook state cache | Hook linked list, queued updates, deps comparison, memoized hook values | Partial | Basic hooks work, but cache invalidation and effect tagging are still simplified | Keep migrating hook bookkeeping toward upstream hook queue/effect list structure |
| Effect tag cache | Hook effect tags and fiber flags determine commit work without recomputing semantics | Partial | Now split into `ReactHookEffectTags`, but still lighter than upstream | Continue separating effect collection from commit execution and preserve tags through all phases |
| Host instance reuse | Host `stateNode` reused; commit mutates host tree instead of rebuilding | Partial | Host nodes/Yoga nodes are reused in many paths, but reuse rules are not fully centralized | Tighten `state_node`/host-node lifecycle so host reuse is authoritative and predictable |
| Child reconciliation cache | Keyed reconciliation reuses existing children rather than rebuilding arrays/instances | Partial | Improved children key traversal exists, but reconciler child reuse is still not upstream-complete | Move further toward keyed child-fiber reuse and subtree diff decisions |
| Thenable/Suspense cache | Thenable status tracked; suspense wakeups reuse cached async state | Partial | Python has resource cache and thenable inspection helpers, but not full upstream thenable protocol | Grow `ReactFiberThenable` into the source of truth for suspense/thenable transitions |
| Error/unwind recovery state | Throw/unwind paths preserve partial work and unwind cleanly | Partial | Boundary modules now exist, but implementation is still thin | Move suspense/error/unwind control flow out of ad hoc try/except blocks into dedicated modules |
| Renderer host context cache | Host context stack avoids recomputing text nesting / host environment state | Partial | Python already maintains host context stack | Mostly keep; align edge-case semantics and propagation rules with upstream |
| Class component update cache | Class update queue stores pending/base updates and force-update markers | Partial | Python has class update queue support, but it is lighter than JS | Continue aligning queue structure and processing order with upstream |
| DevTools inspected element cache | Frontend/backend cache inspected values, paths, and metadata | Partial | Python has inspected element caches and hydration metadata, but payload typing is looser | Keep tightening payload normalization and dehydrated value typing |
| Bridge message normalization cache | DevTools bridge normalizes payloads before dispatch | Partial | Python now has stricter envelope/payload normalization, but still allows more compatibility shortcuts | Incrementally move toward stricter typed message contracts while preserving necessary compatibility |
| Transcript/output cache | Ink renderer may keep previous output for diffing terminal writes | Present, renderer-specific | This exists at renderer/output level, not in core React reconciler | Keep separate from reconciler parity work; do not treat as a substitute for fiber/lane caching |

## Summary

The main JS renderer-level caches are not transcript caches. They are mostly:

- Fiber structure reuse
- Lane/work scheduling state
- Context dependency tracking
- Hook/effect memoization
- Host instance reuse
- Thenable/suspense state

For pyinkcli, the highest-value missing caches are:

1. `childLanes`-style subtree work caching
2. context dependency recording
3. stronger keyed child/fiber reuse
4. fuller thenable/suspense control-state caching
5. more complete throw/unwind recovery state
