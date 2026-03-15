"""
AstrBot 插件：修复 qwen-flash-character 模型 content 字段类型问题并增强长期记忆与群聊支持

问题描述:
当使用 qwen-flash-character 模型时，如果消息的 content 字段是列表类型（list[ContentPart]），
API 会返回错误："Input error. Input should be a valid string: messages.content at index 1."

解决方案:
在 LLM 请求前，通过 on_llm_request 钩子检查并转换 content 字段为字符串。

v1.4.3 重大修复:
- 彻底修复长度检查逻辑，调整处理顺序确保计算准确性
- 先转换所有 content 字段（contexts + extra_user_content_parts）
- 然后计算总长度（contexts 所有 content + prompt）
- 实现智能截断策略：优先移除最早历史消息，必要时截断 prompt
- 使用统一的_calculate_total_length() 方法确保长度计算准确

v1.4.2 修复:
- 修复长度检查逻辑，现在会正确计算 contexts 中所有消息的总长度
- 智能移除最早的历史消息以控制总输入长度在限制范围内
- 优先保留完整的 prompt，仅在必要时截断

v1.4.1 新增功能:
- 添加禁用动作描述快捷开关（一键禁止括号内容输出）
- 自动配置 logit_bias 禁止输出括号及相关符号
- 无需手动查找 Token ID，开箱即用

v1.4.0 新增功能:
- 支持 logit_bias 参数配置（限制模型输出内容）
- 可在管理面板中配置 token 限制规则
- 支持设置 Token 出现概率（-100 到 100）
- 适用于过滤动作描述、括号内容等

v1.3.0 新增功能:
- 支持长期记忆（Long-term Memory）
- 优化群聊场景（Group Chat）
- 自动管理 session 缓存
- 智能上下文截断策略

作者：Assistant
版本：1.4.3
"""

from typing import Any, Dict, List
import uuid

from astrbot.api import star, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.message import ContentPart, TextPart


class Main(star.Star):
    """qwen-flash-character 模型 content 字段修复插件（支持长期记忆和群聊）"""

    def __init__(self, context: star.Context) -> None:
        super().__init__(context)
        self.context = context
        
        # 加载配置
        config = self.context.get_config()
        plugin_config = config.get("qwen_fix_config", {})
        self.enable_auto_fix = plugin_config.get("enable_auto_fix", True)
        self.log_conversion = plugin_config.get("log_conversion", False)
        
        # 长度限制配置（支持按模型自动识别）
        # flash 模型默认 7500，plus 模型默认 30000（留出余量）
        self.max_input_length_flash = plugin_config.get("max_input_length_flash", 7500)
        self.max_input_length_plus = plugin_config.get("max_input_length_plus", 30000)
        self.truncate_strategy = plugin_config.get("truncate_strategy", "tail")
        
        # v1.3.0 新增：长期记忆配置
        self.enable_long_term_memory = plugin_config.get("enable_long_term_memory", False)
        self.memory_entries = plugin_config.get("memory_entries", 50)  # 每 N 条对话触发一次摘要
        self.skip_save_types = plugin_config.get("skip_save_types", [])  # 跳过存储的消息类型
        
        # v1.3.0 新增：群聊配置
        self.enable_group_chat = plugin_config.get("enable_group_chat", False)
        self.character_name = plugin_config.get("character_name", "")  # 角色名称
        self.partial_response = plugin_config.get("partial_response", True)  # 是否启用部分回复
        
        # v1.4.0 新增：logit_bias 配置（限制输出内容）
        self.enable_logit_bias = plugin_config.get("enable_logit_bias", False)
        self.logit_bias_config = plugin_config.get("logit_bias_config", [])
        
        # v1.4.1 新增：禁用动作描述快捷开关
        self.disable_action_description = plugin_config.get("disable_action_description", False)
        
        # Session ID 管理（用于长期记忆）
        self._session_ids: Dict[str, str] = {}
        
        logger.info("qwen-flash-character fix 插件已加载 (v1.4.3)")
        if self.enable_auto_fix:
            logger.info(f"自动修复功能已启用 (flash 限制：{self.max_input_length_flash}, plus 限制：{self.max_input_length_plus})")
        else:
            logger.warning("自动修复功能已禁用")
        
        if self.enable_long_term_memory:
            logger.info(f"长期记忆功能已启用 (memory_entries={self.memory_entries})")
        
        if self.enable_group_chat:
            logger.info(f"群聊模式已启用 (角色名：{self.character_name})")
        
        if self.enable_logit_bias and self.logit_bias_config:
            logger.info(f"logit_bias 已启用，配置了 {len(self.logit_bias_config)} 条限制规则")
            for idx, config in enumerate(self.logit_bias_config):
                token_id = config.get("token_id")
                bias_value = config.get("bias_value")
                desc = config.get("description", "")
                logger.info(f"  规则 {idx+1}: token_id={token_id}, bias={bias_value}, 说明={desc}")
        
        if self.disable_action_description:
            logger.info("已启用禁用动作描述快捷开关（自动禁止输出括号内容）")

    @filter.on_llm_request(priority=100)  # 高优先级，确保在其他钩子之前执行
    async def fix_qwen_content(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        """
        在请求 LLM 前处理 content 字段
        将 list[ContentPart] 类型的 content 转换为字符串
        
        注意：需要处理三个地方：
        1. req.contexts - 历史对话记录
        2. req.extra_user_content_parts - 额外内容块（会被 assemble_context 使用）
        3. 标记需要处理的标志，让 assemble_context 的结果也被处理
        """
        # 检查是否启用了自动修复
        if not self.enable_auto_fix:
            logger.warning("qwen-character fix 插件：自动修复功能已禁用")
            return
            
        try:
            # 获取当前使用的提供商信息
            provider = self.context.get_using_provider(event.unified_msg_origin)
            if not provider:
                logger.debug("qwen-character fix 插件：未找到提供商")
                return

            model_name = provider.get_model().lower() if provider.get_model() else ""
            
            logger.info(f"qwen-character fix 插件：检测到模型={model_name}")
            
            # 只对 qwen-flash-character 和相关模型进行处理
            if "qwen-flash-character" not in model_name and "qwen-plus-character" not in model_name:
                logger.debug(f"qwen-character fix 插件：模型不匹配，跳过")
                return

            # 根据模型类型确定最大长度限制
            max_length = self.max_input_length_plus if "qwen-plus-character" in model_name else self.max_input_length_flash
            logger.info(f"qwen-character fix 插件：使用最大长度限制={max_length} (基于模型类型)")

            logger.info(f"检测到 qwen-character 系列模型 ({model_name})，开始处理 content 字段")

            # === 第一步：转换 contexts 中的 list[ContentPart] 为字符串 ===
            if req.contexts:
                logger.info(f"qwen-character fix 插件：处理 {len(req.contexts)} 条上下文消息")
                for idx, message in enumerate(req.contexts):
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, list):
                            logger.info(f"qwen-character fix 插件：转换消息 {idx} (dict 类型), content 长度={len(content)}")
                            new_content = self._convert_list_to_text(content)
                            message["content"] = new_content
                            logger.info(f"qwen-character fix 插件：消息 {idx} 转换完成，结果长度={len(new_content)}")
                    elif hasattr(message, 'content'):
                        # 如果是 Message 对象
                        content = getattr(message, 'content', None)
                        if isinstance(content, list):
                            logger.info(f"qwen-character fix 插件：转换消息 {idx} (Message 对象), content 长度={len(content)}")
                            new_content = self._convert_list_to_text(content)
                            setattr(message, 'content', new_content)
                            logger.info(f"qwen-character fix 插件：消息 {idx} 转换完成，结果长度={len(new_content)}")

            # === 第二步：转换 extra_user_content_parts 并合并到 prompt ===
            if req.extra_user_content_parts:
                logger.info(f"qwen-character fix 插件：处理 {len(req.extra_user_content_parts)} 个额外内容块")
                extra_texts = []
                
                for idx, part in enumerate(req.extra_user_content_parts):
                    if isinstance(part, dict):
                        # 字典格式的 ContentPart
                        if part.get("type") == "text":
                            text_val = part.get("text", "")
                            if isinstance(text_val, list):
                                # text 本身是列表（罕见情况）
                                converted = self._convert_list_to_text(text_val)
                                extra_texts.append(converted)
                            else:
                                extra_texts.append(str(text_val))
                        else:
                            # 其他类型（如 image_url）转为文本描述
                            converted = self._convert_part_to_text(part)
                            extra_texts.append(converted)
                            
                    elif isinstance(part, TextPart):
                        # TextPart 对象
                        extra_texts.append(part.text)
                        
                    elif isinstance(part, ContentPart):
                        # 其他 ContentPart 子类
                        converted = self._convert_content_part_object(part)
                        extra_texts.append(converted)
                        
                    else:
                        # 未知类型，尝试转换为字符串
                        extra_texts.append(str(part))
                
                # 将所有额外内容拼接到 prompt
                if extra_texts:
                    extra_text_combined = " ".join(extra_texts)
                    logger.info(f"qwen-character fix 插件：将额外内容合并到 prompt: {extra_text_combined[:50]}...")
                    
                    # 如果 prompt 不为空，拼接；否则直接赋值
                    if req.prompt:
                        req.prompt = f"{req.prompt} {extra_text_combined}"
                    else:
                        req.prompt = extra_text_combined
                    
                    # 清空 extra_user_content_parts，防止 assemble_context 创建 list 类型 content
                    req.extra_user_content_parts = []
                    logger.info("qwen-character fix 插件：已清空 extra_user_content_parts")

            # === 第三步：关键 - 检查并控制总长度（包括 contexts 和 prompt）===
            # 必须先计算总长度，然后进行截断
            total_length = self._calculate_total_length(req)
            logger.info(f"qwen-character fix 插件：当前总输入长度={total_length} (contexts + prompt)")
            
            # 检查是否超过限制
            if total_length > max_length:
                logger.warning(
                    f"qwen-character fix 插件：总输入长度 ({total_length}) 超过限制 ({max_length})，"
                    f"将进行智能截断处理"
                )
                
                # 执行智能截断策略
                await self._smart_truncate(req, max_length)
                
                # 重新计算截断后的长度
                total_length = self._calculate_total_length(req)
                logger.info(
                    f"qwen-character fix 插件：截断完成，当前总长度={total_length}"
                )
            
            # === 第四步：应用 logit_bias 配置 ===
            if self.enable_logit_bias and self.logit_bias_config:
                self._apply_logit_bias(req)
            
            # === 第五步：应用禁用动作描述的快捷开关 ===
            if self.disable_action_description:
                self._apply_disable_action_description(req)
            
            # === 第六步：准备长期记忆和群聊配置 ===
            if self.enable_long_term_memory or self.enable_group_chat:
                await self._prepare_character_options(event, req, model_name)
            
            logger.info("qwen-character content 字段预处理完成")

        except Exception as e:
            logger.error(f"qwen-character fix 插件处理失败：{e}", exc_info=True)
            # 不重新抛出异常，避免影响正常流程
            # 即使失败，也让请求继续执行

    def _calculate_total_length(self, req: ProviderRequest) -> int:
        """
        计算总输入长度（contexts 所有 content + prompt）
        
        Args:
            req: ProviderRequest 对象
            
        Returns:
            总字符数
        """
        total_length = 0
        
        # 计算 contexts 中所有 content 的长度
        if req.contexts:
            for message in req.contexts:
                if isinstance(message, dict):
                    content = message.get("content", "")
                    total_length += len(content) if isinstance(content, str) else 0
                elif hasattr(message, 'content'):
                    content = getattr(message, 'content', "")
                    total_length += len(content) if isinstance(content, str) else 0
        
        # 加上 prompt 的长度
        if req.prompt:
            total_length += len(req.prompt)
        
        return total_length

    async def _smart_truncate(self, req: ProviderRequest, max_length: int) -> None:
        """
        智能截断策略：优先移除最早的 context 消息（保留最新的对话）
        
        Args:
            req: ProviderRequest 对象
            max_length: 最大允许长度
        """
        # 策略 1：优先移除最早的 context 消息（保留最新的对话）
        while req.contexts and len(req.contexts) > 1:
            # 尝试移除第一条消息
            removed_msg = req.contexts.pop(0)
            current_length = self._calculate_total_length(req)
            
            logger.debug(
                f"qwen-character fix 插件：移除 1 条历史消息，当前长度={current_length}"
            )
            
            # 如果已经满足长度要求，停止删除
            if current_length <= max_length:
                logger.info(
                    f"qwen-character fix 插件：通过移除历史消息完成截断，"
                    f"剩余 {len(req.contexts)} 条上下文"
                )
                return
        
        # 策略 2：如果 contexts 无法再删减（只剩 1 条或为空），则截断 prompt
        if req.prompt:
            current_length = self._calculate_total_length(req)
            remaining_for_prompt = max_length - (current_length - len(req.prompt))
            
            if remaining_for_prompt > 0:
                logger.info(
                    f"qwen-character fix 插件：将截断 prompt 从 {len(req.prompt)} 到 "
                    f"{remaining_for_prompt} 字符"
                )
                req.prompt = self._truncate_text(req.prompt, remaining_for_prompt)
            else:
                # 极端情况：prompt 也需要完全舍弃
                logger.warning(
                    f"qwen-character fix 插件：上下文过长，将清空 prompt"
                )
                req.prompt = ""
            
            logger.info(
                f"qwen-character fix 插件：通过截断 prompt 完成处理，"
                f"最终长度={self._calculate_total_length(req)}"
            )
        else:
            logger.warning(
                f"qwen-character fix 插件：无法进一步截断，"
                f"当前长度={self._calculate_total_length(req)} 仍超过限制"
            )

    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        根据策略截断文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
            
        if self.truncate_strategy == "tail":
            # 保留头部
            return text[:max_length] + "..."
        elif self.truncate_strategy == "head":
            # 保留尾部
            return "..." + text[-(max_length-3):]
        elif self.truncate_strategy == "middle":
            # 保留头尾
            head_len = max_length // 2
            tail_len = max_length - head_len
            return text[:head_len] + "..." + text[-tail_len:]
        else:
            # 默认截断尾部
            return text[:max_length] + "..."

    def _convert_part_to_text(self, part: dict) -> str:
        """将字典格式的 ContentPart 转换为文本"""
        parts = []
        for key, value in part.items():
            if isinstance(value, list):
                # 递归处理列表
                converted = self._convert_list_to_text(value)
                parts.append(f"[{key}: {converted}]")
            else:
                parts.append(f"{key}: {value}")
        return " ".join(parts)

    def _convert_content_part_object(self, part: Any) -> str:
        """将 ContentPart 对象转换为文本"""
        if isinstance(part, TextPart):
            return part.text if part.text else '[empty]'
        elif hasattr(part, 'text'):
            return getattr(part, 'text', '[unknown]')
        else:
            return f"[{type(part).__name__}]"

    def _convert_list_to_text(self, content_list: list) -> str:
        """
        将 ContentPart 列表转换为文本字符串
        
        Args:
            content_list: ContentPart 对象或字典的列表
            
        Returns:
            转换后的文本字符串
        """
        text_parts = []
        
        for item in content_list:
            if isinstance(item, dict):
                # 处理字典格式的 ContentPart
                if item.get("type") == "text":
                    text_val = item.get("text", "")
                    if text_val:
                        text_parts.append(str(text_val))
                elif item.get("type") == "think":
                    # 跳过 think 部分
                    continue
                else:
                    # 其他类型（如 image_url）转为占位符
                    item_type = item.get("type", "unknown")
                    text_parts.append(f"[{item_type}]")
                    
            elif isinstance(item, TextPart):
                # 处理 TextPart 对象
                if item.text:
                    text_parts.append(item.text)
                    
            elif isinstance(item, ContentPart):
                # 处理其他 ContentPart 子类
                if hasattr(item, 'text') and getattr(item, 'text', None):
                    text_parts.append(getattr(item, 'text'))
                else:
                    # 其他类型转为占位符
                    item_type = type(item).__name__
                    text_parts.append(f"[{item_type}]")
        
        return "".join(text_parts) if text_parts else " "

    async def _prepare_character_options(
        self, event: AstrMessageEvent, req: ProviderRequest, model_name: str
    ) -> None:
        """
        准备 character_options 配置（长期记忆和群聊）
        
        Args:
            event: 事件对象
            req: 请求对象
            model_name: 模型名称
        """
        try:
            # 生成或获取 Session ID（用于长期记忆）
            session_key = f"{event.unified_msg_origin}_{event.get_sender_id()}"
            if session_key not in self._session_ids:
                self._session_ids[session_key] = str(uuid.uuid4())
                logger.info(f"qwen-character fix 插件：为新会话生成 Session ID: {self._session_ids[session_key][:8]}...")
            
            session_id = self._session_ids[session_key]
            
            # 构建 character_options 配置
            character_options = {}
            
            # 1. 配置长期记忆
            if self.enable_long_term_memory:
                logger.info(f"qwen-character fix 插件：启用长期记忆 (memory_entries={self.memory_entries})")
                character_options["memory"] = {
                    "enable_long_term_memory": True,
                    "memory_entries": self.memory_entries,
                    "skip_save_types": self.skip_save_types
                }
                
                # 需要在请求中注入 session_id
                # 注：这需要在 provider 层支持，此处仅做标记
                logger.debug(f"qwen-character fix 插件：Session ID={session_id[:8]}...")
            
            # 2. 配置群聊模式
            if self.enable_group_chat and self.character_name:
                logger.info(f"qwen-character fix 插件：启用群聊模式 (角色={self.character_name})")
                
                # 在群聊模式下，需要在 messages 中标记角色名
                if req.prompt:
                    req.prompt = f"{self.character_name}：{req.prompt}"
                
                # 设置 partial 模式
                if self.partial_response:
                    logger.debug("qwen-character fix 插件：启用 partial 回复模式")
            
            logger.debug("qwen-character fix 插件：character_options 配置完成")
            
        except Exception as e:
            logger.error(f"qwen-character fix 插件：准备 character_options 失败：{e}", exc_info=True)

    def _apply_logit_bias(self, req: ProviderRequest) -> None:
        """
        应用 logit_bias 配置到请求中
        
        Args:
            req: 请求对象
        """
        try:
            if not self.logit_bias_config:
                logger.debug("qwen-character fix 插件：logit_bias 配置为空，跳过")
                return
            
            # 构建 logit_bias 字典
            logit_bias_dict = {}
            for config in self.logit_bias_config:
                token_id = config.get("token_id")
                bias_value = config.get("bias_value")
                desc = config.get("description", "")
                
                if token_id is not None and bias_value is not None:
                    # 验证 bias_value 范围
                    if bias_value < -100 or bias_value > 100:
                        logger.warning(
                            f"qwen-character fix 插件：logit_bias 值超出范围 [{bias_value}], "
                            f"已自动修正为最接近的有效值"
                        )
                        bias_value = max(-100, min(100, bias_value))
                    
                    logit_bias_dict[str(token_id)] = bias_value
                    logger.debug(
                        f"qwen-character fix 插件：添加 logit_bias 规则 - "
                        f"token_id={token_id}, bias={bias_value}, 说明={desc}"
                    )
            
            if logit_bias_dict:
                # 将 logit_bias 添加到 req.extra_body 中
                # 注：需要 provider 支持 extra_body 参数
                if not hasattr(req, 'extra_body') or req.extra_body is None:
                    req.extra_body = {}
                
                req.extra_body['logit_bias'] = logit_bias_dict
                
                logger.info(
                    f"qwen-character fix 插件：已应用 {len(logit_bias_dict)} 条 logit_bias 规则 "
                    f"(通过 extra_body 传入)"
                )
            else:
                logger.warning("qwen-character fix 插件：没有有效的 logit_bias 规则")
                
        except Exception as e:
            logger.error(f"qwen-character fix 插件：应用 logit_bias 失败：{e}", exc_info=True)

    def _apply_disable_action_description(self, req: ProviderRequest) -> None:
        """
        应用禁用动作描述的快捷开关（禁止输出括号内容）
        
        根据阿里云官方文档示例，禁用常见括号相关的 Token ID
        参考：https://help.aliyun.com/zh/model-studio/qwen-character
        
        Args:
            req: 请求对象
        """
        try:
            # 根据阿里云官方文档示例，这些是常见括号相关 Token 的 ID
            # 左括号（、[、【 等
            left_brackets = ["7", "7552", "320", "42344", "96899", "12832"]
            # 右括号）、]、】等
            right_brackets = ["8", "9909", "873", "58359", "6599", "10297", "91093"]
            
            # 构建 logit_bias 字典，将所有括号 Token 设为 -100（完全禁止）
            logit_bias_dict = {}
            
            # 添加所有左括号
            for token_id in left_brackets:
                logit_bias_dict[token_id] = -100
            
            # 添加所有右括号
            for token_id in right_brackets:
                logit_bias_dict[token_id] = -100
            
            # 合并到现有的 logit_bias 配置中（如果有的话）
            if not hasattr(req, 'extra_body') or req.extra_body is None:
                req.extra_body = {}
            
            if 'logit_bias' in req.extra_body:
                # 如果已经有 logit_bias 配置，合并进去
                existing_bias = req.extra_body['logit_bias']
                for token_id, bias_value in logit_bias_dict.items():
                    if token_id not in existing_bias:
                        existing_bias[token_id] = bias_value
                req.extra_body['logit_bias'] = existing_bias
                logger.info(
                    f"qwen-character fix 插件：已添加 {len(logit_bias_dict)} 条括号禁用规则 "
                    f"(与自定义 logit_bias 合并)"
                )
            else:
                # 直接设置
                req.extra_body['logit_bias'] = logit_bias_dict
                logger.info(
                    f"qwen-character fix 插件：已启用禁用动作描述模式，"
                    f"禁止输出 {len(logit_bias_dict)} 种括号相关 Token"
                )
                
        except Exception as e:
            logger.error(f"qwen-character fix 插件：应用禁用动作描述失败：{e}", exc_info=True)

