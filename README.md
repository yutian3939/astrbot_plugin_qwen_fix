# AstrBot Plugin: Qwen Character Fix

修复 qwen-flash-character 和 qwen-plus-character 模型 content 字段类型不匹配问题。

## 功能介绍

当使用阿里云百炼的 qwen-flash-character 或 qwen-plus-character 模型时，如果消息的 content 字段是列表类型（`list[ContentPart]`），API 会返回以下错误：

```
Input error. Input should be a valid string: messages.content at index 1.
```

本插件通过在 LLM 请求前自动检测和转换 content 字段为字符串，解决此兼容性问题。

## 安装方法

### 手动安装

1. 将插件目录复制到 AstrBot 的 `data/plugins/` 目录下
2. 在 AstrBot WebUI 的插件管理处找到本插件
3. 点击"重载插件"即可

### 自动安装（待支持）

未来将支持通过插件市场一键安装。

## 使用方法

安装后无需额外配置，插件会自动检测并使用 qwen-character 系列模型时生效。

### 支持的模型

- `qwen-flash-character`
- `qwen-plus-character`
- 其他包含 `qwen-*-character` 关键字的模型

### 工作原理

1. 插件通过 `on_llm_request` 事件钩子在 LLM 请求前拦截
2. 检查当前使用的模型是否为 qwen-character 系列
3. 如果是，遍历所有消息记录
4. 将 `content` 字段从 `list[ContentPart]` 类型转换为字符串
5. 转换规则：
   - 提取所有文本部分并拼接
   - 忽略思考过程（think 部分）
   - 图片等多媒体内容转为占位符（如 `[image_url]`）

## ⚙️ 配置说明

在 AstrBot WebUI 的插件配置页面，可以调整以下参数：

```json
{
  "qwen_fix_config": {
    "enable_auto_fix": true,              // 是否启用自动修复（默认 true）
    "log_conversion": false,               // 是否记录详细转换日志（默认 false，用于调试）
    "max_input_length_flash": 7500,        // qwen-flash-character 最大长度（模型限制 8000）
    "max_input_length_plus": 30000,        // qwen-plus-character 最大长度（模型限制 32000）
    "truncate_strategy": "tail"            // 文本截断策略（当超过最大长度时）
                                           // - "tail": 保留头部，截断尾部（默认）
                                           // - "head": 截断头部，保留尾部
                                           // - "middle": 保留头尾，截断中间
  }
}
```

### 配置项说明

- **enable_auto_fix**: 控制是否启用自动修复功能。禁用后插件不会处理任何请求。
- **log_conversion**: 开启后会记录详细的转换过程日志，用于调试和排查问题。
- **max_input_length_flash**: qwen-flash-character 模型的输入长度限制。官方限制为 8000 Token，插件默认设置为 7500 以留出余量。
- **max_input_length_plus**: qwen-plus-character 模型的输入长度限制。官方限制为 32000 Token，插件默认设置为 30000 以留出余量。
- **truncate_strategy**: 当转换后的文本超过最大长度时，采用不同的截断策略：
  - `tail`: 保留文本头部，截断尾部（推荐用于对话场景）
  - `head`: 截断头部，保留尾部
  - `middle`: 保留头尾部分，截断中间内容

### 智能识别机制

插件会**自动识别**当前使用的模型类型，并应用相应的长度限制：
- 检测到 `qwen-flash-character` → 使用 `max_input_length_flash` (默认 7500)
- 检测到 `qwen-plus-character` → 使用 `max_input_length_plus` (默认 30000)

无需手动切换配置，插件会根据模型名称自动匹配！

## 注意事项

1. 插件仅在使用 qwen-character 系列模型时生效
2. 对其他模型没有任何影响
3. 使用高优先级（priority=100）确保在其他钩子之前执行
4. 转换后的文本会保留所有原始文本内容，不会丢失信息

## 🔧 故障排除

### 插件未生效

1. 确认插件已正确安装在 `data/plugins/astrbot_plugin_qwen_fix/` 目录
2. 在 AstrBot WebUI 检查插件状态是否为"已加载"
3. 查看日志中是否有 "qwen-flash-character fix 插件已加载" 的提示

### 仍然报错

如果安装后仍然遇到错误，请检查：

1. 日志中是否有详细的错误信息
2. 确认使用的模型名称是否正确
3. 尝试重启 AstrBot 重新加载插件
4. **新增**: 检查日志中的长度提示信息，调整对应的 `max_input_length_*` 配置

### 常见问题场景

#### 场景 1：输入长度超限错误（flash 模型）

**错误信息**:
```
Range of input length should be [1, 8000]
```

**解决方案**:
- 插件 v1.1.0+ 会自动检测并截断超长文本
- 可通过 WebUI 调整 `max_input_length_flash` 配置（不超过 8000）
- 选择合适的 `truncate_strategy` 策略

#### 场景 2：输入长度超限错误（plus 模型）

**错误信息**:
```
Range of input length should be [1, 32000]
```

**解决方案**:
- 插件 v1.1.0+ 会自动检测并截断超长文本
- 可通过 WebUI 调整 `max_input_length_plus` 配置（不超过 32000）
- 选择合适的 `truncate_strategy` 策略

#### 场景 3：转换后内容不完整

**原因**: 文本超过最大长度限制被截断

**解决方案**:
1. 增加对应的 `max_input_length_*` 值（但不超过模型限制）
2. 使用 `middle` 策略保留更多上下文
3. 优化输入内容，减少冗余信息

### 如何知道当前使用的是哪个模型？

查看日志输出：
```
[INFO] qwen-character fix 插件：检测到模型=qwen-flash-character
[INFO] qwen-character fix 插件：使用最大长度限制=7500 (基于模型类型)
```

日志会明确显示当前识别的模型类型和应用的长度限制。

## 📝 更新日志

### v1.2.0 (2026-03-14) - 基于 Qwen-Character 文档优化

- ✨ **智能模型识别**: 自动识别 qwen-flash-character 和 qwen-plus-character，应用不同的长度限制
- ⚙️ **独立配置**: 为不同模型提供独立的长度限制配置项
  - `max_input_length_flash`: 7500（官方限制 8000）
  - `max_input_length_plus`: 30000（官方限制 32000）
- 📊 **精准控制**: 根据模型类型自动匹配最佳配置，无需手动切换
- 📝 **增强日志**: 记录当前使用的模型类型和应用的长度限制

### v1.1.0 (2026-03-14)

- ✨ **新增长度控制功能**: 添加最大输入长度限制，防止超出模型 8000 字符限制
- 🎯 **多种截断策略**: 支持 tail、head、middle 三种文本截断方式
- ⚙️ **可配置参数**: 通过 WebUI 可调整最大长度和截断策略
- 📝 **增强日志记录**: 记录 prompt 长度检查和截断信息
- 🐛 **优化性能**: 改进文本处理逻辑，减少不必要的长度增长

### v1.0.0 (2026-03-08)

- ✨ 初始版本发布
- 🔧 支持自动转换 content 字段
- 🎯 高优先级执行，确保在其他钩子之前处理

## 常见问题

**Q: 这个插件会影响其他模型吗？**

A: 不会。插件只会在使用 qwen-character 系列模型时生效，对其他模型没有任何影响。

**Q: 转换会丢失图片信息吗？**

A: 是的，图片会被转换为 `[image_url]` 占位符文本。但这是必要的，因为 qwen-character API 不支持多模态输入。

**Q: 可以禁用这个插件吗？**

A: 可以在 AstrBot WebUI 的插件管理处停用或卸载本插件。

## 技术支持

如有问题，请在 AstrBot 官方社区或 GitHub 仓库提交 Issue。

## 许可证

与 AstrBot 主项目保持一致。
