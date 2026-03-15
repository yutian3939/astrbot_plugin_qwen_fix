# AstrBot Plugin: Qwen Character Fix

修复 qwen-flash-character 和 qwen-plus-character 模型 content 字段类型不匹配问题，并支持长期记忆、群聊场景和输出内容限制。

## 🔥 v1.4.1 重大更新

### 🌟 新增功能

#### 4. **禁用动作描述快捷开关** ⚡

**解决的问题**:
- 配置 logit_bias 需要手动查找 Token ID，操作复杂
- 用户希望一键禁止模型输出括号内的动作描述
- 降低使用门槛，无需研究 Token 映射表

**功能特性**:
- ✅ 一键启用，无需配置 Token ID
- ✅ 自动应用阿里云官方推荐的括号 Token 列表
- ✅ 完全兼容自定义 logit_bias 配置
- ✅ 开箱即用，简单便捷

**使用方法**:
```json
{
  "disable_action_description": true
}
```

**效果**:
- 启用后自动禁止输出常见括号：`（ ） ( ) [ ] 【 】` 等
- 模型不会输出类似"（朝你挥挥手）"的动作描述
- 可以与自定义 logit_bias 规则同时使用

**与 logit_bias 的关系**:
- `disable_action_description`: 快捷开关，一键禁用括号
- `logit_bias_config`: 高级配置，自定义限制任意 Token
- 两者可以同时使用，自动合并

#### 3. **输出内容限制（Logit Bias）** 🚫

**解决的问题**:
- 模型有时会输出括号内的动作描述，例如：（朝你挥挥手）
- 不希望模型使用某些特定词汇或表达方式
- 需要控制模型的输出风格和格式

**功能特性**:
- ✅ 支持配置 token 出现概率（范围 -100 到 100）
- ✅ 可在管理面板中可视化配置
- ✅ 支持多条规则同时生效
- ✅ 完全禁止或降低特定 token 的可能性
- ✅ 适用于过滤动作描述、括号内容等

**工作原理**:
```json
{
  "logit_bias": {
    "token_id_1": bias_value_1,
    "token_id_2": bias_value_2,
    ...
  }
}
```

- `bias_value = -100`: 完全禁止该 token 出现
- `bias_value = -1`: 减少该 token 被选择的可能性
- `bias_value = 0`: 无影响（默认）
- `bias_value = 1`: 增加该 token 被选择的可能性
- `bias_value = 100`: 强制只选择该 token（不建议，会导致循环输出）

**配置示例**:
```json
{
  "enable_logit_bias": true,
  "logit_bias_config": [
    {
      "token_id": 1234,
      "bias_value": -100,
      "description": "禁止输出左括号（"
    },
    {
      "token_id": 5678,
      "bias_value": -100,
      "description": "禁止输出右括号）"
    },
    {
      "token_id": 9012,
      "bias_value": -50,
      "description": "减少动作描述词汇的使用"
    }
  ]
}
```

**如何获取 Token ID**:
- 下载阿里云提供的 [logit_bias_id 映射表.json](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250908/xtsxix/logit_bias_id%E6%98%A0%E5%B0%84%E8%A1%A8.json)
- 查找需要限制的 token 对应的 ID
- 在插件配置中添加规则

**使用场景**:
1. **过滤动作描述**: 禁止输出括号内的动作描述
2. **规范输出格式**: 禁止使用某些标点符号或格式
3. **风格控制**: 减少口语化表达的使用
4. **专业场景**: 禁止使用非正式词汇

## 🔥 v1.3.0 重大更新

### 🌟 新增功能

#### 1. **长期记忆（Long-term Memory）** 🧠

**解决的问题**：
- qwen-character 系列模型上下文限制为 32K Token，难以支持超长轮次对话
- 对话历史过长会导致关键信息被截断丢失

**功能特性**：
- ✅ 自动对历史对话进行摘要（压缩到 1000 Token 以内）
- ✅ 保留关键上下文信息
- ✅ 支持超长多轮对话（理论上无限轮次）
- ✅ 可配置摘要频率（每 20-400 条对话触发一次）
- ✅ Session ID 自动管理，会话隔离

**工作原理**：
```
第 1 轮：Profile + User_Message_1
第 2 轮：Profile + Summary_1 + User_Message_2 + Assistant_Message_3 + User_Message_4
...
每 N 轮触发一次摘要，保留最近 N 条原始消息 + 历史摘要
```

**配置示例**：
```json
{
  "enable_long_term_memory": true,
  "memory_entries": 50,  // 每 50 条对话触发一次摘要
  "skip_save_types": []  // 跳过存储的消息类型
}
```

#### 2. **群聊模式优化（Group Chat）** 👥

**解决的问题**：
- 多角色对话场景中角色身份识别
- 群聊中的角色名称标记
- 部分回复（partial）控制

**功能特性**：
- ✅ 自动在消息前添加角色名称标记
- ✅ 支持 partial 回复模式（流式输出）
- ✅ 多角色对话历史管理
- ✅ 群聊场景下的上下文拼接

**使用示例**：
```
# 群聊消息格式
messages = [
    {"role": "user", "content": "程毅：周末你们有空不？"},
    {"role": "assistant", "content": "凌路：哼，又来蹭我们专业水平？"},
    {"role": "user", "content": "陶乐：宝贝说得对，不过别熬夜改歌啊"},
]
```

**配置示例**：
```json
{
  "enable_group_chat": true,
  "character_name": "凌路",  // 当前扮演的角色
  "partial_response": true   // 启用 partial 回复
}
```

### ⚙️ 新增配置项

#### 禁用动作描述（v1.4.1）- 推荐新手使用 ⭐

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `disable_action_description` | bool | false | **快捷开关**：一键禁用动作描述（括号内容）。启用后自动配置 logit_bias 禁止输出括号，无需手动查找 Token ID |

**推荐使用场景**:
- 只需要禁止动作描述（括号内容）
- 不想研究 Token 映射表
- 追求简单快捷的配置方式

#### 输出内容限制相关（v1.4.0）

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_logit_bias` | bool | false | 是否启用 logit_bias 限制输出内容 |
| `logit_bias_config` | array | [] | logit_bias 配置列表，每项包含 token_id、bias_value 和 description |

##### logit_bias_config 数组元素结构

每个配置项包含以下字段：

| 字段 | 类型 | 必填 | 范围 | 说明 |
|------|------|------|------|------|
| `token_id` | int | 是 | - | Token 对应的 ID（需从映射表查询） |
| `bias_value` | int | 是 | [-100, 100] | Token 出现概率的调整值 |
| `description` | string | 否 | - | 备注说明，用于标识该规则的用途 |

##### bias_value 取值说明

| 值 | 效果 | 使用场景 |
|----|------|----------|
| `-100` | 完全禁止 | 绝对不允许出现的 token（如括号、动作描述） |
| `-50 ~ -1` | 减少可能性 | 不推荐但可接受的 token |
| `0` | 无影响 | 默认值（通常不需要配置） |
| `1 ~ 50` | 增加可能性 | 推荐使用的表达方式 |
| `51 ~ 99` | 大幅增加可能性 | 强烈推荐的表达方式 |
| `100` | 强制选择 | ❌ 不建议使用，会导致循环输出 |

##### 常用 Token ID 参考

根据阿里云提供的映射表，以下是一些常用的 token ID：

``json
{
  "左括号（": 1234,    // 示例 ID，实际请查映射表
  "右括号（）": 5678,    // 示例 ID，实际请查映射表
  "冒号（:）": 9012,    // 示例 ID，实际请查映射表
  ...
}
```

**重要**: 以上仅为示例，实际 ID 请下载官方映射表查询。

#### 长期记忆相关

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_long_term_memory` | bool | false | 是否启用长期记忆功能 |
| `memory_entries` | int | 50 | 触发记忆摘要的对话条数（范围 20-400） |
| `skip_save_types` | array | [] | 跳过存储的消息类型（user/system/assistant/output） |

#### 群聊相关

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_group_chat` | bool | false | 是否启用群聊模式 |
| `character_name` | string | "" | 群聊中的角色名称（启用群聊时必填） |
| `partial_response` | bool | true | 是否启用 partial 回复模式 |

#### 输出限制配置（v1.4.0+）

- **enable_logit_bias**: 启用 logit_bias 功能，限制模型输出特定内容
  - 默认 `false`：不启用
  - 设置为 `true` 时需要在 `logit_bias_config` 中配置具体规则
  
- **logit_bias_config**: logit_bias 配置列表，数组格式
  - 默认 `[]`：空数组
  - 每项包含三个字段：
    - `token_id` (int): Token 对应的 ID（从官方映射表查询）
    - `bias_value` (int): 概率调整值，范围 `[-100, 100]`
      - `-100`: 完全禁止该 token 出现
      - `-1 ~ -99`: 减少出现的可能性
      - `0`: 无影响（默认）
      - `1 ~ 99`: 增加出现的可能性
      - `100`: 强制只选择该 token（❌ 不建议，会导致循环输出）
    - `description` (string): 备注说明（可选）
  
**使用示例**:

``json
{
  "enable_logit_bias": true,
  "logit_bias_config": [
    {
      "token_id": 1234,  // 替换为实际的左括号 token ID
      "bias_value": -100,
      "description": "禁止输出左括号（"
    },
    {
      "token_id": 5678,  // 替换为实际的右括号 token ID
      "bias_value": -100,
      "description": "禁止输出右括号）"
    },
    {
      "token_id": 9012,  // 替换为实际的动作描述 token ID
      "bias_value": -50,
      "description": "减少动作描述词汇的使用"
    }
  ]
}
```

**如何获取 Token ID**:

1. 下载阿里云官方提供的 [logit_bias_id 映射表.json](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250908/xtsxix/logit_bias_id%E6%98%A0%E5%B0%84%E8%A1%A8.json)
2. 在映射表中查找需要限制的字符或词汇对应的 ID
3. 将 ID 填入配置的 `token_id` 字段

**注意事项**:
- 建议优先使用 `-100` 来完全禁止某些字符（如括号）
- 对于不希望出现但非绝对禁止的词汇，使用 `-50 ~ -1` 的范围
- 避免使用 `100`，这会导致模型循环输出同一个 token
- 可以配置多条规则，同时限制多个 token

### 🔧 技术实现

#### Session ID 管理

插件会自动为每个会话生成唯一的 Session ID：

```
# Session Key 生成规则
session_key = f"{platform}_{user_id}"
session_id = uuid.uuid4()

# 示例
session_key = "qq_12345678"
session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

#### character_options 配置

插件会自动构建以下配置结构：

```
{
  "character_options": {
    "profile": "角色人设信息...",
    "memory": {
      "enable_long_term_memory": true,
      "memory_entries": 50,
      "skip_save_types": []
    }
  }
}
```

#### Header 注入

长期记忆需要在请求 Header 中添加：

```
x-dashscope-aca-session: {session_id}
```

### 📊 性能对比

| 场景 | v1.2.0 | v1.3.0 | 提升 |
|------|--------|--------|------|
| 短对话（<50 轮） | ✅ 正常 | ✅ 正常 | 无变化 |
| 长对话（50-200 轮） | ❌ 截断丢失 | ✅ 完整保留 | 显著提升 |
| 超长对话（>200 轮） | ❌ 无法处理 | ✅ 流畅对话 | 质的飞跃 |
| 群聊单角色 | ✅ 正常 | ✅ 增强 | 更好的上下文管理 |
| 群聊多角色 | ⚠️ 需手动管理 | ✅ 自动管理 | 大幅简化 |

### 🎯 使用场景

#### 场景 1：长篇角色扮演剧情

**需求**：与虚拟角色进行数十甚至上百轮的连续对话

**v1.2.0 问题**：
- 超过 32K Token 后内容被截断
- 遗忘早期重要剧情
- 角色设定逐渐模糊

**v1.3.0 解决方案**：
- 启用长期记忆：`"enable_long_term_memory": true`
- 设置合适的摘要频率：`"memory_entries": 50`
- 自动保留关键剧情和角色关系

#### 场景 2：音乐人群聊 / 工作群讨论

**需求**：多个角色在同一聊天场景中互动

**v1.2.0 问题**：
- 需要手动拼接角色名称
- partial 回复控制复杂
- 上下文管理混乱

**v1.3.0 解决方案**：
- 启用群聊模式：`"enable_group_chat": true`
- 设置角色名：`"character_name": "凌路"`
- 自动处理角色标记和部分回复

#### 场景 3：用户偏好记忆

**需求**：记住用户的喜好、习惯等个人信息

**v1.3.0 能力**：
```
用户：我最喜欢吃蓝莓了
...（中间经过 100 轮对话）...
AI：要不要一起去买蓝莓？我记得你最喜欢这个
```

通过长期记忆，自动提取并保留用户画像信息。

### 📝 完整配置示例

#### 配置 1：个人助理（启用长期记忆）

```json
{
  "qwen_fix_config": {
    "enable_auto_fix": true,
    "max_input_length_flash": 7500,
    "max_input_length_plus": 30000,
    "truncate_strategy": "tail",
    
    // 长期记忆配置
    "enable_long_term_memory": true,
    "memory_entries": 50,
    "skip_save_types": ["system"]
  }
}
```

#### 配置 2：群聊 NPC（启用群聊模式）

```json
{
  "qwen_fix_config": {
    "enable_auto_fix": true,
    "max_input_length_plus": 30000,
    
    // 群聊配置
    "enable_group_chat": true,
    "character_name": "江让",
    "partial_response": true,
    
    // 可选：同时启用长期记忆
    "enable_long_term_memory": true,
    "memory_entries": 100
  }
}
```

#### 配置 3：游戏 NPC（综合场景）

```json
{
  "qwen_fix_config": {
    "enable_auto_fix": true,
    "max_input_length_plus": 30000,
    "truncate_strategy": "middle",
    
    // 群聊 + 长期记忆
    "enable_group_chat": true,
    "character_name": "凌路",
    "partial_response": true,
    
    "enable_long_term_memory": true,
    "memory_entries": 30,
    "skip_save_types": ["output"]  // 不保存模型输出，节省空间
    
    // v1.4.1: 一键禁用动作描述（推荐新手使用）
    "disable_action_description": true,
    
    // v1.4.0: 自定义 logit_bias 限制（高级功能）
    "enable_logit_bias": true,
    "logit_bias_config": [
      {
        "token_id": 1234,  // 替换为实际的左括号 token ID
        "bias_value": -100,
        "description": "禁止输出左括号"
      },
      {
        "token_id": 5678,  // 替换为实际的右括号 token ID
        "bias_value": -100,
        "description": "禁止输出右括号"
      }
    ]
  }
}
```

## 📋 原始功能介绍

当使用阿里云百炼的 qwen-flash-character 或 qwen-plus-character 模型时，如果消息的 content 字段是列表类型（`list[ContentPart]`），API 会返回以下错误：

```
Input error. Input should be a valid string: messages.content at index 1.
```

本插件通过在 LLM 请求前自动检测和转换 content 字段为字符串，解决此兼容性问题。

## 🚀 安装方法

### 手动安装

1. 将插件目录复制到 AstrBot 的 `data/plugins/` 目录下
2. 在 AstrBot WebUI 的插件管理处找到本插件
3. 点击"重载插件"即可

### 自动安装（待支持）

未来将支持通过插件市场一键安装。

## 📖 使用方法

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
6. **新增**: 检查总长度，如超过限制则按策略截断
7. **新增**: 准备长期记忆和群聊配置

## ⚙️ 配置说明

在 AstrBot WebUI 的插件配置页面，可以调整以下参数：

```
{
  "qwen_fix_config": {
    "enable_auto_fix": true,              // 是否启用自动修复（默认 true）
    "log_conversion": false,               // 是否记录详细转换日志（默认 false，用于调试）
    "max_input_length_flash": 7500,        // qwen-flash-character 最大长度（模型限制 8000）
    "max_input_length_plus": 30000,        // qwen-plus-character 最大长度（模型限制 32000）
    "truncate_strategy": "tail",           // 文本截断策略（当超过最大长度时）
                                           // - "tail": 保留头部，截断尾部（默认）
                                           // - "head": 截断头部，保留尾部
                                           // - "middle": 保留头尾，截断中间
    
    // v1.3.0 新增配置
    "enable_long_term_memory": false,      // 是否启用长期记忆（默认 false）
    "memory_entries": 50,                  // 触发摘要的对话条数（20-400）
    "skip_save_types": [],                 // 跳过存储的消息类型
    
    "enable_group_chat": false,            // 是否启用群聊模式（默认 false）
    "character_name": "",                  // 群聊中的角色名称
    "partial_response": true               // 是否启用 partial 回复
    
    // v1.4.1 新增配置（推荐新手使用 ⭐）
    "disable_action_description": false,   // 一键禁用动作描述（括号内容），无需配置 Token ID
    
    // v1.4.0 新增配置（高级自定义）
    "enable_logit_bias": false,            // 是否启用 logit_bias 限制输出（默认 false）
    "logit_bias_config": []                // logit_bias 配置列表（见下方详细说明）
  }
}
```

### 配置项说明

#### 基础配置

- **enable_auto_fix**: 控制是否启用自动修复功能。禁用后插件不会处理任何请求。
- **log_conversion**: 开启后会记录详细的转换过程日志，用于调试和排查问题。
- **max_input_length_flash**: qwen-flash-character 模型的输入长度限制。官方限制为 8000 Token，插件默认设置为 7500 以留出余量。
- **max_input_length_plus**: qwen-plus-character 模型的输入长度限制。官方限制为 32000 Token，插件默认设置为 30000 以留出余量。
- **truncate_strategy**: 当转换后的文本超过最大长度时，采用不同的截断策略：
  - `tail`: 保留文本头部，截断尾部（推荐用于对话场景）
  - `head`: 截断头部，保留尾部
  - `middle`: 保留头尾部分，截断中间内容

#### 长期记忆配置（v1.3.0+）

- **enable_long_term_memory**: 启用后支持超长对话，自动对历史对话进行摘要
- **memory_entries**: 设置每多少条对话触发一次摘要（范围 20-400）
  - 较小值（20-30）：频繁摘要，保留更多细节，但增加 Token 消耗
  - 较大值（100-200）：减少摘要频率，节省 Token，但可能丢失细节
  - 推荐值：50（平衡性能和成本）
- **skip_save_types**: 指定不希望被记入长期记忆的消息类型
  - `system`: 系统消息（如临时指令）
  - `user`: 用户消息（如一次性查询）
  - `assistant`: 助手消息（如预定义回复）
  - `output`: 模型生成的输出
  - 默认 `[]`：保存所有类型的消息

#### 群聊配置（v1.3.0+）

- **enable_group_chat**: 启用群聊模式，自动处理多角色对话
- **character_name**: 当前 AI 扮演的角色名称（启用群聊时必填）
  - 示例：`"凌路"`, `"江让"`, `"程毅"`
- **partial_response**: 启用 partial 回复模式（流式输出）
  - 推荐在群聊场景中开启
  - 提供更好的对话流畅性

#### 禁用动作描述（v1.4.1+）⭐ 推荐新手使用

- **disable_action_description**: 一键禁用动作描述的快捷开关
  - 默认 `false`：不启用
  - 设置为 `true` 后：
    - ✅ 自动禁止输出常见括号：`（ ） ( ) [ ] 【 】` 等
    - ✅ 无需手动查找 Token ID
    - ✅ 自动应用阿里云官方推荐的 Token 列表
    - ✅ 可以与自定义 logit_bias 配置同时使用
  
**使用示例**:
```json
{
  "disable_action_description": true
}
```

**效果对比**:

启用前:
```
你好啊！（朝你挥挥手，脸上带着微笑）
```

启用后:
```
你好啊！今天过得怎么样？
```

**注意事项**:
- 该功能会自动处理常见的中文和英文括号
- 如果只需要禁用动作描述，推荐使用此快捷开关
- 如果需要更精细的控制（如限制特定词汇），请使用 logit_bias_config

#### 输出限制配置（v1.4.0+）

- **enable_logit_bias**: 启用 logit_bias 功能，限制模型输出特定内容
  - 默认 `false`：不启用
  - 设置为 `true` 时需要在 `logit_bias_config` 中配置具体规则
  
- **logit_bias_config**: logit_bias 配置列表，数组格式
  - 默认 `[]`：空数组
  - 每项包含三个字段：
    - `token_id` (int): Token 对应的 ID（从官方映射表查询）
    - `bias_value` (int): 概率调整值，范围 `[-100, 100]`
      - `-100`: 完全禁止该 token 出现
      - `-1 ~ -99`: 减少出现的可能性
      - `0`: 无影响（默认）
      - `1 ~ 99`: 增加出现的可能性
      - `100`: 强制只选择该 token（❌ 不建议，会导致循环输出）
    - `description` (string): 备注说明（可选）
  
**使用示例**:

``json
{
  "enable_logit_bias": true,
  "logit_bias_config": [
    {
      "token_id": 1234,  // 替换为实际的左括号 token ID
      "bias_value": -100,
      "description": "禁止输出左括号（"
    },
    {
      "token_id": 5678,  // 替换为实际的右括号 token ID
      "bias_value": -100,
      "description": "禁止输出右括号）"
    },
    {
      "token_id": 9012,  // 替换为实际的动作描述 token ID
      "bias_value": -50,
      "description": "减少动作描述词汇的使用"
    }
  ]
}
```

**如何获取 Token ID**:

1. 下载阿里云官方提供的 [logit_bias_id 映射表.json](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250908/xtsxix/logit_bias_id%E6%98%A0%E5%B0%84%E8%A1%A8.json)
2. 在映射表中查找需要限制的字符或词汇对应的 ID
3. 将 ID 填入配置的 `token_id` 字段

**注意事项**:
- 建议优先使用 `-100` 来完全禁止某些字符（如括号）
- 对于不希望出现但非绝对禁止的词汇，使用 `-50 ~ -1` 的范围
- 避免使用 `100`，这会导致模型循环输出同一个 token
- 可以配置多条规则，同时限制多个 token

### 智能识别机制

插件会**自动识别**当前使用的模型类型，并应用相应的长度限制：
- 检测到 `qwen-flash-character` → 使用 `max_input_length_flash` (默认 7500)
- 检测到 `qwen-plus-character` → 使用 `max_input_length_plus` (默认 30000)

无需手动切换配置，插件会根据模型名称自动匹配！

## ⚠️ 注意事项

1. 插件仅在使用 qwen-character 系列模型时生效
2. 对其他模型没有任何影响
3. 使用高优先级（priority=100）确保在其他钩子之前执行
4. 转换后的文本会保留所有原始文本内容，不会丢失信息
5. **新增**: 当文本超过限制时会自动截断，可能丢失部分内容
6. **新增**: 长期记忆功能会增加额外的 Token 消耗（用于生成摘要）
7. **新增**: 群聊模式需要正确设置角色名称才能正常工作
8. **新增**: Session ID 会自动管理，365 天未使用的会话会被系统自动清除

## 🔧 故障排除

### 插件未生效

1. 确认插件已正确安装在 `data/plugins/astrbot_plugin_qwen_fix/` 目录
2. 在 AstrBot WebUI 检查插件状态是否为"已加载"
3. 查看日志中是否有 "qwen-flash-character fix 插件已加载 (v1.3.0)" 的提示

### 仍然报错

如果安装后仍然遇到错误，请检查：

1. 日志中是否有详细的错误信息
2. 确认使用的模型名称是否正确
3. 尝试重启 AstrBot 重新加载插件
4. **新增**: 检查日志中的长度提示信息，调整对应的 `max_input_length_*` 配置
5. **新增**: 长期记忆功能需要 qwen-plus-character 模型支持
6. **新增**: 群聊模式需要确保角色名称配置正确

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

#### 场景 3：长期记忆未生效

**现象**：对话超过 memory_entries 条后仍未触发摘要

**排查步骤**：
1. 检查 `enable_long_term_memory` 是否为 true
2. 查看日志中是否有 "启用长期记忆" 的记录
3. 确认使用的是 qwen-plus-character 模型（flash 不支持）
4. 检查 `memory_entries` 设置是否在有效范围（20-400）

#### 场景 4：群聊中角色识别错误

**现象**：AI 回复时没有使用正确的角色名称

**排查步骤**：
1. 检查 `character_name` 是否已配置
2. 确认 `enable_group_chat` 是否为 true
3. 查看日志中是否有 "启用群聊模式" 的记录
4. 检查消息格式是否正确（需要在 content 中标记角色名）

#### 场景 5：转换后内容不完整

**原因**: 文本超过最大长度限制被截断

**解决方案**:
1. 增加对应的 `max_input_length_*` 值（但不超过模型限制）
2. 使用 `middle` 策略保留更多上下文
3. 优化输入内容，减少冗余信息
4. **推荐**: 启用长期记忆功能支持超长对话

#### 场景 6：如何过滤动作描述（括号内容）

**需求**: 不希望模型输出类似"（朝你挥挥手）"这样的动作描述

**解决方案 1 - 推荐新手使用 ⭐**:

``json
{
  "disable_action_description": true
}
```

**优点**:
- ✅ 一键启用，无需配置
- ✅ 自动处理所有常见括号
- ✅ 不需要研究 Token 映射表

**解决方案 2 - 高级自定义**:

1. 下载阿里云提供的 [logit_bias_id 映射表.json](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250908/xtsxix/logit_bias_id%E6%98%A0%E5%B0%84%E8%A1%A8.json)
2. 查找左右括号对应的 token ID
3. 在插件配置中添加 logit_bias 规则：

``json
{
  "enable_logit_bias": true,
  "logit_bias_config": [
    {
      "token_id": <左括号的 ID>,
      "bias_value": -100,
      "description": "禁止输出左括号"
    },
    {
      "token_id": <右括号的 ID>,
      "bias_value": -100,
      "description": "禁止输出右括号"
    }
  ]
}
```

4. 重启 AstrBot 或重新加载插件使配置生效

**效果**: 模型将无法输出包含括号的文本，从而避免动作描述。

**注意**: Token ID 需要从官方映射表中查询，不同字符的 ID 可能不同。

**两种方案的区别**:
- **快捷开关**: 简单方便，适合只需要禁用括号的场景
- **自定义 logit_bias**: 灵活强大，可以限制任意 Token，但需要手动配置

### 如何知道当前使用的是哪个模型？

查看日志输出：
```
[INFO] qwen-character fix 插件：检测到模型=qwen-flash-character
[INFO] qwen-character fix 插件：使用最大长度限制=7500 (基于模型类型)
```

日志会明确显示当前识别的模型类型和应用的长度限制。

### 如何知道长期记忆是否在工作？

查看日志：
```
[INFO] qwen-character fix 插件：启用长期记忆 (memory_entries=50)
[DEBUG] qwen-character fix 插件：Session ID=a1b2c3d4...
```

如果看到这些信息，说明长期记忆功能已正常启用。

## 📝 更新日志

### v1.4.1 (2026-03-15) - 添加禁用动作描述快捷开关

- ✨ **快捷开关功能**: 新增 `disable_action_description` 配置项，一键禁用动作描述
- 🎯 **自动配置**: 启用后自动应用阿里云官方推荐的括号 Token 列表
- ⚡ **开箱即用**: 无需查找 Token ID，降低使用门槛
- 🛠️ **兼容性强**: 可与自定义 logit_bias 配置同时使用
- 📊 **覆盖全面**: 自动处理常见括号：`（ ） ( ) [ ] 【 】` 等
- 📝 **增强日志**: 记录禁用动作描述的启用状态

### v1.4.0 (2026-03-15) - 支持输出内容限制（Logit Bias）

- ✨ **logit_bias 功能**: 支持配置 token 出现概率，限制模型输出特定内容
- 🎯 **管理面板配置**: 可在 AstrBot WebUI 中可视化配置 logit_bias 规则
- ⚙️ **灵活的偏置控制**: 支持 [-100, 100] 范围的值，从完全禁止到强制选择
- 🛠️ **新增配置项**: 
  - `enable_logit_bias`: 启用 logit_bias 功能
  - `logit_bias_config`: logit_bias 规则列表（包含 token_id、bias_value、description）
- 📊 **应用场景**: 
  - 过滤动作描述（括号内容）
  - 规范输出格式
  - 控制输出风格
- 📝 **增强日志**: 记录 logit_bias 规则的应用情况

### v1.3.0 (2026-03-14) - 支持长期记忆和群聊场景

- ✨ **长期记忆功能**: 支持超长对话，自动摘要历史对话（压缩到 1000 Token 以内）
- 🎯 **群聊模式优化**: 自动管理多角色对话，支持角色名称标记
- ⚙️ **Session ID 管理**: 自动生成和管理会话标识，支持会话隔离
- 🛠️ **新增配置项**: 
  - `enable_long_term_memory`: 启用长期记忆
  - `memory_entries`: 摘要频率控制
  - `skip_save_types`: 跳过存储的消息类型
  - `enable_group_chat`: 启用群聊模式
  - `character_name`: 角色名称
  - `partial_response`: partial 回复控制
- 📊 **性能提升**: 支持理论上无限轮次的对话
- 📝 **增强日志**: 记录长期记忆和群聊相关的状态信息

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

## ❓ 常见问题

**Q: 这个插件会影响其他模型吗？**

A: 不会。插件只会在使用 qwen-character 系列模型时生效，对其他模型没有任何影响。

**Q: 转换会丢失图片信息吗？**

A: 是的，图片会被转换为 `[image_url]` 占位符文本。但这是必要的，因为 qwen-character API 不支持多模态输入。

**Q: 可以禁用这个插件吗？**

A: 可以在 AstrBot WebUI 的插件管理处停用或卸载本插件。

**Q: 如何知道文本是否被截断了？**

A: 查看日志，如果文本被截断会有明确的警告信息，显示原始长度和截断后的长度。

**Q: 哪种截断策略最好？**

A: 
- 日常对话场景：推荐 `tail`（保留最新内容）
- 代码/技术文档：推荐 `head`（保留关键信息）
- 需要上下文：推荐 `middle`（平衡头尾）

**Q: 长期记忆功能有什么限制吗？**

A: 
- 仅支持中文场景
- 仅 qwen-plus-character 模型支持（flash 不支持）
- 会产生额外的 Token 消耗（用于生成摘要）
- 摘要会压缩到 1000 Token 以内，无法完整保留所有细节

**Q: memory_entries 应该设置为多少？**

A: 
- 短对话场景（<50 轮）：50-100
- 中等对话（50-200 轮）：30-50
- 超长对话（>200 轮）：20-30
- 推荐从默认值 50 开始，根据实际情况调整

**Q: 群聊模式如何使用？**

A: 
1. 设置 `enable_group_chat: true`
2. 配置 `character_name` 为你的角色名称
3. 建议开启 `partial_response: true`
4. 在消息内容中标记角色名（如："凌路：你好"）

**Q: Session ID 会过期吗？**

A: 会的。系统会自动清除 365 天内未使用的会话。如需长期保存，请定期使用该会话。

## 🔗 技术支持

如有问题，请在 AstrBot 官方社区或 GitHub 仓库提交 Issue。

## 📄 许可证

与 AstrBot 主项目保持一致。

---

**最后更新**: 2026-03-15  
**当前版本**: v1.4.1  
**参考文档**: 阿里云百炼 Qwen-Character 官方文档
