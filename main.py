"""
牛客文章获取插件 - AstrBot Plugin
智能识别链接/关键词，简化交互流程
"""
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .services import SessionManager, close_session
from .handlers import handle_search


@register("nowcoder_helper", "domye", "智能获取牛客文章", "1.0.0")
class NowcoderHelperPlugin(Star):
    """牛客文章助手插件"""

    def __init__(self, context: Context):
        super().__init__(context)
        data_path = Path(get_astrbot_data_path()) / "plugin_data" / "nowcoder_helper"
        self.session_manager = SessionManager(data_path)

    async def initialize(self):
        """插件初始化"""
        logger.info("Nowcoder Helper Plugin initialized")

    @filter.regex(r'^牛客')
    async def nowcoder(self, event: AstrMessageEvent):
        """智能获取牛客文章。用法: 牛客 <关键词> [筛选类型] [排序方式]"""
        full_msg = event.message_str.strip()
        msg = full_msg[2:].strip() if full_msg.startswith('牛客') else full_msg

        async for result in handle_search(event, msg, self.session_manager):
            yield result

    async def terminate(self):
        """插件销毁"""
        await close_session()
        logger.info("Nowcoder Helper Plugin terminated")