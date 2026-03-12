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

## 配置说明

本插件无需配置，开箱即用。

## 注意事项

1. 插件仅在使用 qwen-character 系列模型时生效
2. 对其他模型没有任何影响
3. 使用高优先级（priority=100）确保在其他钩子之前执行
4. 转换后的文本会保留所有原始文本内容，不会丢失信息

## 故障排除

### 插件未生效

1. 确认插件已正确安装在 `data/plugins/astrbot_plugin_qwen_fix/` 目录
2. 在 AstrBot WebUI 检查插件状态是否为"已加载"
3. 查看日志中是否有 "qwen-flash-character fix 插件已加载" 的提示

### 仍然报错

如果安装后仍然遇到错误，请检查：

1. 日志中是否有详细的错误信息
2. 确认使用的模型名称是否正确
3. 尝试重启 AstrBot 重新加载插件

## 更新日志

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
