# JS/Python 文件命名和结构对比审计报告

## 1. 源文件目录结构对比

### 1.1 主目录文件对比 (js_source/ink/src/ vs src/pyinkcli/)

| JS 文件 | Python 文件 | 状态 | 备注 |
|---------|-------------|------|------|
| ansi-tokenizer.ts | ansi_tokenizer.py | ✅ 已翻译 | |
| colorize.ts | colorize.py | ✅ 已翻译 | |
| cursor-helpers.ts | cursor_helpers.py | ✅ 已翻译 | |
| devtools.ts | devtools.py | ✅ 已翻译 | |
| devtools-window-polyfill.ts | devtools_window_polyfill.py | ✅ 已翻译 | |
| dom.ts | dom.py | ✅ 已翻译 | |
| get-max-width.ts | get_max_width.py | ✅ 已翻译 | |
| index.ts | index.py | ✅ 已翻译 | |
| ink.tsx | ink.py | ✅ 已翻译 | |
| input-parser.ts | input_parser.py | ✅ 已翻译 | |
| instances.ts | instances.py | ✅ 已翻译 | |
| kitty-keyboard.ts | kitty_keyboard.py | ✅ 已翻译 | |
| log-update.ts | log_update.py | ✅ 已翻译 | |
| measure-element.ts | measure_element.py | ✅ 已翻译 | |
| measure-text.ts | measure_text.py | ✅ 已翻译 | |
| output.ts | output.py | ✅ 已翻译 | |
| parse-keypress.ts | parse_keypress.py | ✅ 已翻译 | |
| reconciler.ts | reconciler.py | ✅ 已翻译 | |
| render-background.ts | render_background.py | ✅ 已翻译 | |
| render-border.ts | render_border.py | ✅ 已翻译 | |
| render-node-to-output.ts | render_node_to_output.py | ✅ 已翻译 | |
| render-to-string.ts | render_to_string.py | ✅ 已翻译 | |
| render.ts | render.py | ✅ 已翻译 | |
| renderer.ts | renderer.py | ✅ 已翻译 | |
| sanitize-ansi.ts | sanitize_ansi.py | ✅ 已翻译 | |
| squash-text-nodes.ts | squash_text_nodes.py | ✅ 已翻译 | |
| styles.ts | styles.py | ✅ 已翻译 | |
| utils.ts | utils.py | ✅ 已翻译 | |
| wrap-text.ts | wrap_text.py | ✅ 已翻译 | |
| write-synchronized.ts | write_synchronized.py | ✅ 已翻译 | |

### 1.2 Components 目录对比

| JS 文件 | Python 文件 | 状态 | 备注 |
|---------|-------------|------|------|
| AccessibilityContext.ts | AccessibilityContext.py | ✅ 已翻译 | |
| AppContext.ts | AppContext.py | ✅ 已翻译 | |
| App.tsx | App.py | ✅ 已翻译 | |
| BackgroundContext.ts | BackgroundContext.py | ✅ 已翻译 | |
| Box.tsx | Box.py | ✅ 已翻译 | |
| CursorContext.ts | CursorContext.py | ✅ 已翻译 | |
| ErrorBoundary.tsx | ErrorBoundary.py | ✅ 已翻译 | |
| ErrorOverview.tsx | ErrorOverview.py | ✅ 已翻译 | |
| FocusContext.ts | FocusContext.py | ✅ 已翻译 | |
| Newline.tsx | Newline.py | ✅ 已翻译 | |
| Spacer.tsx | Spacer.py | ✅ 已翻译 | |
| Static.tsx | Static.py | ✅ 已翻译 | |
| StderrContext.ts | StderrContext.py | ✅ 已翻译 | |
| StdinContext.ts | StdinContext.py | ✅ 已翻译 | |
| StdoutContext.ts | StdoutContext.py | ✅ 已翻译 | |
| Text.tsx | Text.py | ✅ 已翻译 | |
| Transform.tsx | Transform.py | ✅ 已翻译 | |

**缺失检查**: JS 目录中没有其他文件，Python 已完全对应。

### 1.3 Hooks 目录对比

| JS 文件 | Python 文件 | 状态 | 备注 |
|---------|-------------|------|------|
| use-app.ts | use_app.py | ✅ 已翻译 | |
| use-box-metrics.ts | use_box_metrics.py | ✅ 已翻译 | |
| use-cursor.ts | use_cursor.py | ✅ 已翻译 | |
| use-focus-manager.ts | use_focus_manager.py | ✅ 已翻译 | |
| use-focus.ts | use_focus.py | ✅ 已翻译 | |
| use-input.ts | use_input.py | ✅ 已翻译 | |
| use-is-screen-reader-enabled.ts | use_is_screen_reader_enabled.py | ✅ 已翻译 | |
| use-paste.ts | use_paste.py | ✅ 已翻译 | |
| use-stderr.ts | use_stderr.py | ✅ 已翻译 | |
| use-stdin.ts | use_stdin.py | ✅ 已翻译 | |
| use-stdout.ts | use_stdout.py | ✅ 已翻译 | |
| use-window-size.ts | use_window_size.py | ✅ 已翻译 | |

**Python 额外文件**:
- `state.py` - Python 特有的状态管理模块（JS 中使用 React 内置 useState）

### 1.4 Utils 目录对比

| JS 文件 | Python 文件 | 状态 | 备注 |
|---------|-------------|------|------|
| (无独立 utils 目录) | ansi_escapes.py | ⚠️ Python 特有 | JS 中使用 ansi-escapes 包 |
| (无独立 utils 目录) | cli_boxes.py | ⚠️ Python 特有 | JS 中使用 cli-boxes 包 |
| (无独立 utils 目录) | string_width.py | ⚠️ Python 特有 | JS 中使用 string-width 包 |
| (无独立 utils 目录) | wrap_ansi.py | ⚠️ Python 特有 | JS 中使用 wrap-ansi 包 |
| (无独立 utils 目录) | __init__.py | ⚠️ Python 特有 | Python 包初始化文件 |

**说明**: Python 的 utils 目录包含的是外部依赖的内部实现，这些在 JS 中是独立的 npm 包。

### 1.5 缺失的 JS 文件（Python 中没有对应）

| JS 文件 | 用途 | Python 中如何处理 |
|---------|------|------------------|
| global.d.ts | TypeScript 全局类型定义 | 不需要（Python 有类型提示） |

## 2. 测试文件对比

### 2.1 JS 测试文件 (js_source/ink/test/)

JS 测试文件列表（主要文件）：
- ansi-tokenizer.ts
- sanitize-ansi.ts
- input-parser.ts
- render.tsx
- components.tsx
- cursor.tsx
- focus.tsx
- hooks.tsx
- log-update.tsx
- measure-element.tsx
- measure-text.tsx
- text.tsx
- use-box-metrics.tsx
- width-height.tsx
- 等等...

### 2.2 Python 测试文件 (tests/)

| Python 测试文件 | 对应 JS 测试 | 状态 |
|-----------------|-------------|------|
| test_ansi_tokenizer.py | ansi-tokenizer.ts | ✅ 对应 |
| test_sanitize_ansi.py | sanitize-ansi.ts | ✅ 对应 |
| test_input_parser.py | input-parser.ts | ✅ 对应 |
| test_reconciler_incremental.py | reconciler.tsx | ⚠️ 部分对应 |
| test_cursor_helpers.py | cursor-helpers.tsx | ✅ 对应 |
| test_focus_runtime.py | focus.tsx | ✅ 对应 |
| test_hooks.py | hooks.tsx | ✅ 对应 |
| test_log_update_runtime.py | log-update.tsx | ✅ 对应 |
| test_measure_element.py | measure-element.tsx | ❌ 缺失 |
| test_measure_text.py | measure-text.tsx | ❌ 缺失 |
| test_text.py | text.tsx | ✅ 对应 |
| test_box.py | components.tsx/width-height.tsx | ✅ 对应 |
| test_render_instance.py | render.tsx | ✅ 对应 |
| test_get_max_width.py | get-max-width.ts | ✅ 对应 |
| test_squash_text_nodes.py | squash-text-nodes.ts | ✅ 对应 |
| test_examples_directory_parity.py | (无) | ⚠️ Python 特有 |
| test_examples_smoke.py | (无) | ⚠️ Python 特有 |
| test_index_exports.py | (无) | ⚠️ Python 特有 |
| test_output_buffer.py | output.ts | ✅ 对应 |
| test_parse_keypress.py | parse-keypress.ts | ✅ 对应 |
| test_runtime_semantics.py | (无) | ⚠️ Python 特有 |
| test_text_sanitize_integration.py | (无) | ⚠️ Python 特有 |
| test_user_output_sanitize.py | sanitize-ansi.ts | ✅ 对应 |
| test_background_render.py | background.tsx | ✅ 对应 |
| test_ansi_escapes.py | (无) | ⚠️ Python 特有 |
| test_cli_boxes.py | (无) | ⚠️ Python 特有 |
| test_string_width.py | (无) | ⚠️ Python 特有 |

## 3. Examples 目录对比

### 3.1 JS Examples (js_source/ink/examples/)

| Example 目录 | 主文件 | 状态 |
|-------------|--------|------|
| alternate-screen | alternate-screen.tsx | ✅ |
| aria | aria.tsx | ✅ |
| borders | borders.tsx | ✅ |
| box-backgrounds | box-backgrounds.tsx | ✅ |
| chat | chat.tsx | ✅ |
| concurrent-suspense | concurrent-suspense.tsx | ✅ |
| counter | counter.tsx | ✅ |
| cursor-ime | cursor-ime.tsx | ✅ |
| incremental-rendering | incremental-rendering.tsx | ✅ |
| jest | jest.tsx, summary.tsx, test.tsx | ✅ |
| justify-content | justify-content.tsx | ✅ |
| router | router.tsx | ✅ |
| select-input | select-input.tsx | ✅ |
| static | static.tsx | ✅ |
| suspense | suspense.tsx | ✅ |
| subprocess-output | subprocess-output.tsx | ✅ |
| table | table.tsx | ✅ |
| terminal-resize | terminal-resize.tsx | ✅ |
| use-focus | use-focus.tsx | ✅ |
| use-focus-with-id | use-focus-with-id.tsx | ✅ |
| use-input | use-input.tsx | ✅ |
| use-stderr | use-stderr.tsx | ✅ |
| use-stdout | use-stdout.tsx | ✅ |
| use-transition | use-transition.tsx | ✅ |

### 3.2 Python Examples (examples/)

所有 JS examples 在 Python 中都有对应，命名采用 kebab-case 到 snake_case 转换。

## 4. 命名规范转换规则

| JS 命名规范 | Python 命名规范 | 示例 |
|------------|----------------|------|
| kebab-case 文件名 | snake_case 文件名 | use-input.ts → use_input.py |
| camelCase 函数名 | snake_case 函数名 | useInput → use_input |
| PascalCase 类名 | PascalCase 类名 | Box → Box |
| camelCase 属性名 | snake_case 属性名 | isActive → is_active |

## 5. 需要修复的问题

### 5.1 文件名不完全对应的问题

目前所有主要源文件都已经正确对应，没有文件名不匹配的问题。

### 5.2 类名/函数名需要检查的文件

以下是需要进一步检查类名、函数名是否完全对应的文件：

1. `ink.py` - 主类 Ink 需要检查方法名
2. `reconciler.py` - React reconciler 的翻译，需要检查钩子函数名
3. `dom.py` - DOM 操作相关函数
4. `styles.py` - 样式转换函数
5. `hooks/state.py` - Python 特有的状态管理

### 5.3 缺失的测试覆盖

以下 JS 测试在 Python 中没有对应：
- flex-align-content.tsx
- flex-align-items.tsx
- flex-align-self.tsx
- flex-direction.tsx
- flex-justify-content.tsx
- flex-wrap.tsx
- margin.tsx
- padding.tsx
- position.tsx
- overflow.tsx

## 6. 总结

### 6.1 文件命名 parity 状态

- **主源文件**: 100% 对应
- **Components**: 100% 对应
- **Hooks**: 100% 对应（state.py 为 Python 特有）
- **Utils**: Python 有额外的内部实现（替代 npm 包）

### 6.2 需要关注的点

1. 测试覆盖率需要增加，特别是 Flexbox 相关测试
2. 需要验证所有导出的 API 名称是否完全对应
3. 需要验证 examples 是否都能正常运行
