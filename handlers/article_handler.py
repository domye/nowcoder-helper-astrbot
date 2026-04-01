"""
文章URL处理器
"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from ..services import fetch_article, build_article_message, RE_NOWCODER_URL


async def handle_article_url(event: AstrMessageEvent, url: str):
    """处理文章URL"""
    try:
        yield event.plain_result("正在获取文章...")
        article = await fetch_article(url)
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


def extract_url_from_message(message: str) -> str:
    """从消息中提取牛客URL"""
    match = RE_NOWCODER_URL.search(message)
    return match.group(0) if match else None