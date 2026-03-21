# Stress Test Examples - 性能压力测试

这些例子用于测试和演示 pyinkcli 在大量组件情况下的渲染性能。

## 测试例子

### 1. 基础压力测试 (stress-test.py)

测试大量列表项在持续更新时的性能表现。

```bash
# 默认测试 (500 个元素)
python stress-test.py

# 自定义元素数量
python stress-test.py --items 1000

# 启用并发模式
python stress-test.py --items 1000 --concurrent

# 更快更新频率
python stress-test.py --items 500 --update-interval 0.5
```

**功能特性：**
- 可配置数量的列表项 (默认 500)
- 自动周期性更新 (默认每 1 秒更新 10% 的项)
- 实时 FPS 和渲染时间显示
- 支持键盘导航 (上下箭头、PageUp/PageDown)
- 按 `T` 键暂停/恢复自动更新
- 按 `R` 键重置数据

### 2. 极端压力测试 (stress-test-extreme.py)

**专门设计用于复现 UI 冻结问题**。使用故意慢的计算来模拟真实应用中的重负载。

### 3. 对比测试 (stress-test-compare.py)

**并排对比 Sync 和 Concurrent 模式的差异**。左侧是同步渲染，右侧是并发渲染。

```bash
# 默认对比 (300 个元素)
python stress-test-compare.py

# 自定义元素数量和计算延迟
python stress-test-compare.py --items 500 --delay 5
```

**说明：**
- 左侧 (红色)：Sync 模式 - 每次更新都会阻塞 UI
- 右侧 (绿色)：Concurrent 模式 - 更新可以被中断，UI 保持响应

```bash
# 默认测试 (1000 个元素，同步模式 - 会卡!)
python stress-test-extreme.py

# 更多元素 (小心！会更卡)
python stress-test-extreme.py --items 2000

# 并发模式对比
python stress-test-extreme.py --items 1000 --concurrent
```

**警告：** 此测试故意使用 5ms/项的计算时间，1000 项 = 每帧 5 秒计算时间！

## 观察指标

| FPS | 状态 | 说明 |
|-----|------|------|
| > 30 | GOOD | 流畅 |
| 10-30 | LAGGY | 有卡顿 |
| < 10 | FREEZING | 严重卡顿/冻结 |

## 性能问题分析

当组件数量很大时，每次更新会导致：

1. **整个组件树重新渲染**
2. **useMemo 缓存失效**，触发大量重新计算
3. **单线程阻塞** - Python GIL 导致无法并行

## 对比测试

对比同步模式和并发模式的差异：

```bash
# 同步模式 (卡顿)
python stress-test-extreme.py --items 500

# 并发模式 (应该更流畅)
python stress-test-extreme.py --items 500 --concurrent
```

## 键盘控制

| 按键 | 功能 |
|------|------|
| ↑↓ | 上下导航 |
| PageUp/PageDown | 快速翻页 |
| R | 重置数据 |
| T | 暂停/恢复更新 (stress-test.py) |
| Enter | 手动触发更新 |
| Ctrl+C | 退出 |

**对比测试专用控制 (stress-test-compare.py)：**
| 按键 | 功能 |
|------|------|
| ↑ | 触发 Sync 更新 |
| ↓ | 触发 Concurrent 更新 |
| Enter | 同时触发两种更新 |

## 建议测试场景

1. **基准测试**: `--items 100` - 建立性能基准
2. **中等负载**: `--items 500` - 模拟真实应用
3. **压力测试**: `--items 1000+` - 测试极限
4. **并发对比**: 同配置对比 sync vs concurrent

## 调试建议

如果发现性能问题：

1. 减少不必要的 `useMemo` 依赖
2. 使用 `useTransition` 将非关键更新降级
3. 虚拟化长列表 (只渲染可见区域)
4. 考虑使用 React.memo 类似的组件记忆化
