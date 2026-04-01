"""
牛客文章获取插件 - AstrBot Plugin
获取牛客文章并以 Markdown 格式返回
"""
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .services.api_client import fetch_article, fetch_search_results
from .services.models import Article


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

    # 统计信息
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

    # 图片
    if article.feed_images:
        lines.append('\n\n---\n\n**图片**:\n\n')
        lines.append('\n'.join(f'![图片]({u})' for u in article.feed_images))

    return ''.join(lines)


@register("nowcoder_helper", "domye", "获取牛客文章并以 Markdown 格式返回", "1.0.0")
class NowcoderHelperPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化"""
        logger.info("Nowcoder Helper Plugin initialized")

    @filter.command("nowcoder")
    async def fetch_nowcoder_article(self, event: AstrMessageEvent, url: str):
        """获取牛客文章。用法: /nowcoder <文章URL>"""
        try:
            logger.info(f"Fetching article from: {url}")
            article = fetch_article(url)
            markdown = article_to_markdown(article)
            yield event.plain_result(markdown)
        except ValueError as e:
            yield event.plain_result(f"错误: 无法识别的URL格式。请提供牛客文章链接。\n支持格式:\n- https://www.nowcoder.com/discuss/xxx\n- https://www.nowcoder.com/feed/main/detail/xxx")
        except Exception as e:
            logger.error(f"Failed to fetch article: {e}")
            yield event.plain_result(f"获取文章失败: {str(e)}")

    @filter.command("nowcoder_search")
    async def search_nowcoder(self, event: AstrMessageEvent, keyword: str):
        """搜索牛客文章。用法: /nowcoder_search <关键词>"""
        try:
            logger.info(f"Searching for: {keyword}")
            result = fetch_search_results(keyword, page=1)

            if not result.items:
                yield event.plain_result(f"未找到相关文章: {keyword}")
                return

            # 构建搜索结果列表
            lines = [f"## 搜索结果: {keyword}\n\n"]
            lines.append(f"共找到 {len(result.items)} 条结果 (第 1 页，共 {result.total_pages} 页)\n\n")
            lines.append("---\n\n")

            for i, item in enumerate(result.items, 1):
                lines.append(f"{i}. **{item.title}**\n")
                lines.append(f"   类型: {item.article_type}\n")
                lines.append(f"   链接: {item.to_url()}\n\n")

            lines.append(f"\n提示: 使用 /nowcoder <链接> 获取文章详情")

            yield event.plain_result(''.join(lines))
        except Exception as e:
            logger.error(f"Search failed: {e}")
            yield event.plain_result(f"搜索失败: {str(e)}")

    async def terminate(self):
        """插件销毁"""
        logger.info("Nowcoder Helper Plugin terminated")