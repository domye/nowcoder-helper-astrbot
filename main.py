"""
牛客文章获取插件 - AstrBot Plugin
交互式获取牛客文章并以 Markdown 格式返回
"""
import json
import asyncio
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .services.api_client_async import fetch_article, fetch_search_results
from .services.models import Article, SearchResult


def article_to_markdown(article: Article) -> str:
    """将文章转换为 Markdown 格式"""
    lines = [
        f"# {article.title or '无标题'}\n\n",
        f"**作者**: {article.author or '未知'}\n",
    ]
    if article.identity:
        lines.append(f"**身份**: {article.identity}\n")
    if article.post_time:
        lines.append(f"**时间**: {article.post_time}\n")
    lines.append(f"**链接**: {article.url}\n\n")

    stats = []
    if article.view_count:
        stats.append(f"浏览 {article.view_count}")
    if article.like_count:
        stats.append(f"点赞 {article.like_count}")
    if article.comment_count:
        stats.append(f"评论 {article.comment_count}")
    if stats:
        lines.append(f"**统计**: {' | '.join(stats)}\n\n")

    lines.append("---\n\n")
    lines.append(article.content or '无内容')

    if article.feed_images:
        lines.append('\n\n---\n\n**图片**:\n\n')
        lines.append('\n'.join(f'![图片]({u})' for u in article.feed_images))

    return ''.join(lines)


@register("nowcoder_helper", "domye", "交互式获取牛客文章", "1.0.0")
class NowcoderHelperPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_path = get_astrbot_data_path() / "plugin_data" / "nowcoder_helper"
        self.sessions_file = self.data_path / "sessions.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        self.data_path.mkdir(parents=True, exist_ok=True)
        if not self.sessions_file.exists():
            self.sessions_file.write_text(json.dumps({}, encoding='utf-8'))

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

    @filter.command("nowcoder")
    async def start_nowcoder(self, event: AstrMessageEvent):
        """启动牛客助手交互会话"""
        sender_id = event.get_sender_id()

        # 检查是否有未完成的会话
        sessions = self._load_sessions()
        if sender_id in sessions:
            yield event.plain_result("你有一个未完成的会话，请继续操作或发送'退出'取消")
            return

        yield event.plain_result(
            "牛客文章助手已启动\n\n"
            "请选择功能:\n"
            "1. 解析文章 (发送链接)\n"
            "2. 搜索文章 (发送关键词)\n\n"
            "发送数字选择，或发送'退出'取消"
        )

        @session_waiter(timeout=60, record_history_chains=False)
        async def nowcoder_session(controller: SessionController, ev: AstrMessageEvent):
            msg = ev.message_str.strip()

            if msg == "退出":
                await ev.send(ev.plain_result("已退出牛客助手"))
                # 清理会话状态
                sessions = self._load_sessions()
                if sender_id in sessions:
                    del sessions[sender_id]
                    self._save_sessions(sessions)
                controller.stop()
                return

            # 获取当前会话状态
            sessions = self._load_sessions()
            session_data = sessions.get(sender_id, {"step": "select_function"})

            # 步骤1: 选择功能
            if session_data["step"] == "select_function":
                if msg == "1":
                    session_data["step"] = "parse_url"
                    sessions[sender_id] = session_data
                    self._save_sessions(sessions)
                    await ev.send(ev.plain_result("请发送牛客文章链接\n支持格式:\n- https://www.nowcoder.com/discuss/xxx\n- https://www.nowcoder.com/feed/main/detail/xxx"))
                    controller.keep(timeout=60, reset_timeout=True)
                elif msg == "2":
                    session_data["step"] = "search_keyword"
                    sessions[sender_id] = session_data
                    self._save_sessions(sessions)
                    await ev.send(ev.plain_result("请输入搜索关键词"))
                    controller.keep(timeout=60, reset_timeout=True)
                else:
                    await ev.send(ev.plain_result("无效选择，请发送 1 或 2"))
                    controller.keep(timeout=60, reset_timeout=True)
                return

            # 步骤2: 解析文章URL
            if session_data["step"] == "parse_url":
                try:
                    await ev.send(ev.plain_result("正在获取文章..."))
                    article = await fetch_article(msg)
                    markdown = article_to_markdown(article)
                    await ev.send(ev.plain_result(markdown))
                except ValueError:
                    await ev.send(ev.plain_result("无效的URL格式，请发送正确的牛客文章链接"))
                    controller.keep(timeout=60, reset_timeout=True)
                    return
                except Exception as e:
                    await ev.send(ev.plain_result(f"获取文章失败: {str(e)}"))
                    controller.keep(timeout=60, reset_timeout=True)
                    return

                # 清理会话状态并结束
                if sender_id in sessions:
                    del sessions[sender_id]
                    self._save_sessions(sessions)
                controller.stop()
                return

            # 步骤3: 搜索关键词
            if session_data["step"] == "search_keyword":
                try:
                    await ev.send(ev.plain_result("正在搜索..."))
                    result = await fetch_search_results(msg, page=1)

                    if not result.items:
                        await ev.send(ev.plain_result(f"未找到相关文章: {msg}\n请重新输入关键词或发送'退出'"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return

                    # 保存搜索状态
                    session_data["step"] = "select_article"
                    session_data["keyword"] = msg
                    session_data["current_page"] = 1
                    session_data["total_pages"] = result.total_pages
                    session_data["log_id"] = result.log_id
                    session_data["session_id"] = result.session_id
                    sessions[sender_id] = session_data
                    self._save_sessions(sessions)

                    # 显示搜索结果
                    response = self._format_search_results(result, msg, 1)
                    await ev.send(ev.plain_result(response))
                    controller.keep(timeout=60, reset_timeout=True)
                except Exception as e:
                    await ev.send(ev.plain_result(f"搜索失败: {str(e)}"))
                    controller.keep(timeout=60, reset_timeout=True)
                return

            # 步骤4: 选择文章或翻页
            if session_data["step"] == "select_article":
                keyword = session_data["keyword"]
                current_page = session_data["current_page"]
                total_pages = session_data["total_pages"]
                log_id = session_data.get("log_id")
                session_id = session_data.get("session_id")

                # 翻页处理
                if msg == "下一页" or msg == "next":
                    if current_page >= total_pages:
                        await ev.send(ev.plain_result("已经是最后一页了"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return
                    try:
                        next_page = current_page + 1
                        await ev.send(ev.plain_result(f"正在加载第 {next_page} 页..."))
                        result = await fetch_search_results(keyword, page=next_page, log_id=log_id, session_id=session_id)

                        session_data["current_page"] = next_page
                        session_data["log_id"] = result.log_id
                        session_data["session_id"] = result.session_id
                        sessions[sender_id] = session_data
                        self._save_sessions(sessions)

                        response = self._format_search_results(result, keyword, next_page)
                        await ev.send(ev.plain_result(response))
                        controller.keep(timeout=60, reset_timeout=True)
                    except Exception as e:
                        await ev.send(ev.plain_result(f"翻页失败: {str(e)}"))
                        controller.keep(timeout=60, reset_timeout=True)
                    return

                if msg == "上一页" or msg == "prev":
                    if current_page <= 1:
                        await ev.send(ev.plain_result("已经是第一页了"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return
                    try:
                        prev_page = current_page - 1
                        await ev.send(ev.plain_result(f"正在加载第 {prev_page} 页..."))
                        result = await fetch_search_results(keyword, page=prev_page, log_id=log_id, session_id=session_id)

                        session_data["current_page"] = prev_page
                        session_data["log_id"] = result.log_id
                        session_data["session_id"] = result.session_id
                        sessions[sender_id] = session_data
                        self._save_sessions(sessions)

                        response = self._format_search_results(result, keyword, prev_page)
                        await ev.send(ev.plain_result(response))
                        controller.keep(timeout=60, reset_timeout=True)
                    except Exception as e:
                        await ev.send(ev.plain_result(f"翻页失败: {str(e)}"))
                        controller.keep(timeout=60, reset_timeout=True)
                    return

                # 选择文章编号
                try:
                    index = int(msg)
                    # 需要重新获取当前页的结果来选择文章
                    result = await fetch_search_results(keyword, page=current_page, log_id=log_id, session_id=session_id)

                    if index < 1 or index > len(result.items):
                        await ev.send(ev.plain_result(f"无效编号，请选择 1-{len(result.items)} 之间的数字"))
                        controller.keep(timeout=60, reset_timeout=True)
                        return

                    item = result.items[index - 1]
                    await ev.send(ev.plain_result("正在获取文章..."))
                    article = await fetch_article(item.to_url())
                    markdown = article_to_markdown(article)
                    await ev.send(ev.plain_result(markdown))

                    # 清理会话状态
                    if sender_id in sessions:
                        del sessions[sender_id]
                        self._save_sessions(sessions)
                    controller.stop()
                except ValueError:
                    await ev.send(ev.plain_result("请输入数字选择文章，或发送'下一页'/'上一页'翻页，'退出'取消"))
                    controller.keep(timeout=60, reset_timeout=True)
                except Exception as e:
                    await ev.send(ev.plain_result(f"获取文章失败: {str(e)}"))
                    controller.keep(timeout=60, reset_timeout=True)
                return

        try:
            await nowcoder_session(event)
        except TimeoutError:
            # 清理超时用户的会话状态
            sessions = self._load_sessions()
            if sender_id in sessions:
                del sessions[sender_id]
                self._save_sessions(sessions)
            yield event.plain_result("会话超时（1分钟），已自动退出牛客助手")
        finally:
            event.stop_event()

    def _format_search_results(self, result: SearchResult, keyword: str, page: int) -> str:
        """格式化搜索结果"""
        lines = [
            f"搜索结果: {keyword}\n",
            f"第 {page} 页 / 共 {result.total_pages} 页\n",
            f"共 {len(result.items)} 条结果\n\n",
            "---\n\n"
        ]

        for i, item in enumerate(result.items, 1):
            lines.append(f"{i}. {item.title}\n")

        lines.append("\n---\n\n")
        lines.append("输入编号选择文章\n")
        if page < result.total_pages:
            lines.append("发送'下一页'查看更多\n")
        if page > 1:
            lines.append("发送'上一页'返回\n")
        lines.append("发送'退出'取消")

        return ''.join(lines)

    async def terminate(self):
        """插件销毁"""
        logger.info("Nowcoder Helper Plugin terminated")