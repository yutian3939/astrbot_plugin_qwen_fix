"""
AstrBot 插件：修复 qwen-flash-character 模型 content 字段类型问题

问题描述:
当使用 qwen-flash-character 模型时，如果消息的 content 字段是列表类型（list[ContentPart]），
API 会返回错误："Input error. Input should be a valid string: messages.content at index 1."

解决方案:
在 LLM 请求前，通过 on_llm_request 钩子检查并转换 content 字段为字符串。

作者：Assistant
版本：1.0.0
"""

from typing import Any

from astrbot.api import star, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.message import ContentPart, TextPart


class Main(star.Star):
    """qwen-flash-character 模型 content 字段修复插件"""

    def __init__(self, context: star.Context) -> None:
        super().__init__(context)
        self.context = context
        
        # 加载配置
        config = self.context.get_config()
        plugin_config = config.get("qwen_fix_config", {})
        self.enable_auto_fix = plugin_config.get("enable_auto_fix", True)
        self.log_conversion = plugin_config.get("log_conversion", False)
        
        # 新增：最大长度限制配置（支持按模型自动识别）
        # flash 模型默认 7500，plus 模型默认 30000（留出余量）
        self.max_input_length_flash = plugin_config.get("max_input_length_flash", 7500)
        self.max_input_length_plus = plugin_config.get("max_input_length_plus", 30000)
        self.truncate_strategy = plugin_config.get("truncate_strategy", "tail")
        
        logger.info("qwen-flash-character fix 插件已加载")
        if self.enable_auto_fix:
            logger.info(f"自动修复功能已启用 (flash 限制：{self.max_input_length_flash}, plus 限制：{self.max_input_length_plus})")
        else:
            logger.warning("自动修复功能已禁用")

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

            # 1. 处理 contexts 中的 content 字段
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

            # 2. 关键策略：处理 extra_user_content_parts
            # 将它们转换为文本并拼接到 req.prompt，然后清空 extra_user_content_parts
            # 这样 assemble_context 会因为 text 非空且 extra_user_content_parts 为空而返回简单格式
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

            # 3. 新增：检查并控制总长度
            if req.prompt:
                prompt_length = len(req.prompt)
                logger.info(f"qwen-character fix 插件：当前 prompt 长度={prompt_length}")
                
                if prompt_length > max_length:
                    logger.warning(
                        f"qwen-character fix 插件：prompt 长度 ({prompt_length}) 超过限制 ({max_length})，"
                        f"将进行截断处理"
                    )
                    req.prompt = self._truncate_text(req.prompt, max_length)
                    logger.info(
                        f"qwen-character fix 插件：prompt 已截断至 {len(req.prompt)} 字符，"
                        f"使用策略：{self.truncate_strategy}"
                    )

            logger.info("qwen-character content 字段预处理完成")

        except Exception as e:
            logger.error(f"qwen-character fix 插件处理失败：{e}", exc_info=True)
            # 不重新抛出异常，避免影响正常流程
            # 即使失败，也让请求继续执行

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
