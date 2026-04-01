"""
牛客文章获取插件 - AstrBot Plugin
智能识别链接/关键词，简化交互流程
"""
import json
import re
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import astrbot.api.message_components as Comp

from .services.api_client_async import (
    fetch_article, fetch_search_results, close_session,
    SEARCH_TAG_IDS, SEARCH_ORDER_TYPES
)
from .services.models import Article, SearchResult

# URL 正则
RE_NOWCODER_URL = re.compile(r'https?://www\.nowcoder\.com/(discuss/\d+|feed/main/detail/[a-f0-9]+)')


def format_article_text(article: Article) -> str:
    """将文章转换为简洁的文本格式（不含图片）"""
    lines = [
        f"{article.title or '无标题'}\n\n",
        article.content or '无内容'
    ]
    return ''.join(lines)


def build_article_message(article: Article):
    """构建文章消息（包含图片则发送图片）"""
    text = format_article_text(article)

    if not article.feed_images:
        return text, []

    chain = [Comp.Plain(text), Comp.Plain("\n")]
    for img_url in article.feed_images:
        chain.append(Comp.Image.fromURL(img_url))

    return None, chain


@register("nowcoder_helper", "domye", "智能获取牛客文章", "1.0.0")
class NowcoderHelperPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_path = Path(get_astrbot_data_path()) / "plugin_data" / "nowcoder_helper"
        self.sessions_file = self.data_path / "sessions.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        self.data_path.mkdir(parents=True, exist_ok=True)
        if not self.sessions_file.exists():
            self.sessions_file.write_text(json.dumps({}), encoding='utf-8')

    def _load_sessions(self) -> dict:
        """加载会话状态"""
        try:
            return json.loads(self.sessions_file.read_text(encoding='utf-8'))
        except:
            return {}

    def _save_sessions(self, sessions: dict):
        """保存会话状态"""
        self.sessions_file.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding='utf-8')

    async def initialize(self):
        """插件初始化"""
        logger.info("Nowcoder Helper Plugin initialized")

    @filter.command("牛客")
    async def nowcoder(self, event: AstrMessageEvent, query: str = ""):
        """智能获取牛客文章。用法: /牛客 <关键词> [筛选类型] [排序方式]"""
        sender_id = event.get_sender_id()
        msg = query.strip()

        # 检查是否有未完成的会话
        sessions = self._load_sessions()
        if sender_id in sessions:
            yield event.plain_result("你有未完成的搜索会话，请继续选择或发送'退出'")
            return

        # 无参数：显示帮助
        if not msg:
            tag_types = " | ".join(SEARCH_TAG_IDS.keys())
            yield event.plain_result(
                "📖 牛客文章助手\n\n"
                "用法:\n"
                "/牛客 <链接> - 解析文章\n"
                "/牛客 <关键词> - 搜索文章\n"
                "/牛客 <关键词> <筛选> - 筛选类型\n"
                "/牛客 <关键词> 最新 - 最新排序\n\n"
                f"筛选类型: {tag_types}\n"
                "排序方式: 最新\n\n"
                "示例:\n"
                "/牛客 https://www.nowcoder.com/discuss/123456\n"
                "/牛客 阿里 面经\n"
                "/牛客 字节 最新"
            )
            return

        # 检测是否为链接
        url_match = RE_NOWCODER_URL.search(msg)
        if url_match:
            # 直接解析文章
            try:
                yield event.plain_result("正在获取文章...")
                article = await fetch_article(msg)
                text, chain = build_article_message(article)
                if chain:
                    yield event.chain_result(chain)
                else:
                    yield event.plain_result(text)
            except ValueError:
                yield event.plain_result("无效的URL格式")
            except Exception as e:
                logger.error(f"Failed to fetch article: {e}")
                yield event.plain_result(f"获取文章失败: {str(e)}")
            return

        # 解析搜索参数：关键词 [筛选类型] [排序方式]
        parts = msg.split()
        keyword = parts[0]
        tag_type = None
        order = ''

        # 解析第二个参数（可能是筛选类型或排序）
        if len(parts) >= 2:
            if parts[1] in SEARCH_TAG_IDS:
                tag_type = parts[1]
            elif parts[1] == '最新':
                order = SEARCH_ORDER_TYPES.get('最新', 'create')

        # 解析第三个参数（只能是排序）
        if len(parts) >= 3 and parts[2] == '最新':
            order = SEARCH_ORDER_TYPES.get('最新', 'create')

        # 搜索文章
        try:
            search_info = keyword
            if tag_type:
                search_info += f" | 筛选: {tag_type}"
            if order:
                search_info += " | 排序: 最新"
            yield event.plain_result(f"正在搜索: {search_info}...")

            result = await fetch_search_results(keyword, page=1, tag_type=tag_type, order=order)

            if not result.items:
                yield event.plain_result(f"未找到相关文章: {search_info}")
                return

            # 保存搜索状态（包含筛选和排序）
            sessions[sender_id] = {
                "keyword": keyword,
                "tag_type": tag_type,
                "order": order,
                "current_page": 1,
                "total_pages": result.total_pages,
                "log_id": result.log_id,
                "session_id": result.session_id
            }
            self._save_sessions(sessions)

            # 显示搜索结果并进入会话
            response = self._format_search_results(result, keyword, 1, tag_type, order)
            yield event.plain_result(response)

            # 启动会话等待选择
            @session_waiter(timeout=60, record_history_chains=False)
            async def select_article(controller: SessionController, ev: AstrMessageEvent):
                user_msg = ev.message_str.strip()

                if user_msg == "退出":
                    if sender_id in sessions:
                        del sessions[sender_id]
                        self._save_sessions(sessions)
                    await ev.send(ev.plain_result("已退出"))
                    controller.stop()
                    return

                session_data = sessions.get(sender_id, {})
                keyword = session_data.get("keyword", msg)
                tag_type = session_data.get("tag_type")
                order = session_data.get("order", '')
                current_page = session_data.get("current_page", 1)
                total_pages = session_data.get("total_pages", 1)
                log_id = session_data.get("log_id")
                session_id = session_data.get("session_id")

                # 翻页
                if user_msg in ("下一页", "next"):
                    if current_page >= total_pages:
                        await ev.send(ev.plain_result("已是最后一页"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return
                    new_page = current_page + 1
                    try:
                        result = await fetch_search_results(keyword, page=new_page, log_id=log_id, session_id=session_id, tag_type=tag_type, order=order)
                        sessions[sender_id]["current_page"] = new_page
                        sessions[sender_id]["log_id"] = result.log_id
                        sessions[sender_id]["session_id"] = result.session_id
                        self._save_sessions(sessions)
                        await ev.send(ev.plain_result(self._format_search_results(result, keyword, new_page, tag_type, order)))
                        controller.keep(timeout=60, reset_timeout=True)
                    except Exception as e:
                        await ev.send(ev.plain_result(f"翻页失败: {e}"))
                        controller.keep(timeout=60, reset_timeout=True)
                    return

                if user_msg in ("上一页", "prev"):
                    if current_page <= 1:
                        await ev.send(ev.plain_result("已是第一页"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return
                    new_page = current_page - 1
                    try:
                        result = await fetch_search_results(keyword, page=new_page, log_id=log_id, session_id=session_id, tag_type=tag_type, order=order)
                        sessions[sender_id]["current_page"] = new_page
                        sessions[sender_id]["log_id"] = result.log_id
                        sessions[sender_id]["session_id"] = result.session_id
                        self._save_sessions(sessions)
                        await ev.send(ev.plain_result(self._format_search_results(result, keyword, new_page, tag_type, order)))
                        controller.keep(timeout=60, reset_timeout=True)
                    except Exception as e:
                        await ev.send(ev.plain_result(f"翻页失败: {e}"))
                        controller.keep(timeout=60, reset_timeout=True)
                    return

                # 选择文章
                try:
                    index = int(user_msg)
                    result = await fetch_search_results(keyword, page=current_page, log_id=log_id, session_id=session_id, tag_type=tag_type, order=order)
                    if index < 1 or index > len(result.items):
                        await ev.send(ev.plain_result(f"无效编号，请选择 1-{len(result.items)}"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return

                    item = result.items[index - 1]
                    await ev.send(ev.plain_result("正在获取文章..."))
                    article = await fetch_article(item.to_url())
                    text, chain = build_article_message(article)
                    if chain:
                        await ev.send(ev.chain_result(chain))
                    else:
                        await ev.send(ev.plain_result(text))

                    if sender_id in sessions:
                        del sessions[sender_id]
                        self._save_sessions(sessions)
                    controller.stop()
                except ValueError:
                    await ev.send(ev.plain_result("请输入编号、'下一页'、'上一页'或'退出'"))
                    controller.keep(timeout=60, reset_timeout=True)
                except Exception as e:
                    await ev.send(ev.plain_result(f"获取失败: {e}"))
                    controller.keep(timeout=60, reset_timeout=True)

            try:
                await select_article(event)
            except TimeoutError:
                if sender_id in sessions:
                    del sessions[sender_id]
                    self._save_sessions(sessions)
                yield event.plain_result("会话超时，已退出")
            finally:
                event.stop_event()

        except Exception as e:
            logger.error(f"Search failed: {e}")
            yield event.plain_result(f"搜索失败: {str(e)}")

    def _format_search_results(self, result: SearchResult, keyword: str, page: int, tag_type: str = None, order: str = '') -> str:
        """格式化搜索结果"""
        search_info = f"🔍 搜索: {keyword}"
        if tag_type:
            search_info += f" | 筛选: {tag_type}"
        if order:
            search_info += " | 排序: 最新"

        lines = [f"{search_info}\n第{page}页/共{result.total_pages}页\n\n"]

        for i, item in enumerate(result.items, 1):
            lines.append(f"{i}. {item.title}\n")

        lines.append("\n输入编号查看文章")
        if page < result.total_pages:
            lines.append("，'下一页'翻页")
        if page > 1:
            lines.append("，'上一页'返回")
        lines.append("，'退出'取消")

        return ''.join(lines)

    async def terminate(self):
        """插件销毁"""
        await close_session()
        logger.info("Nowcoder Helper Plugin terminated")