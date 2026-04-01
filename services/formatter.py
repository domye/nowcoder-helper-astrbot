"""
消息格式化
"""
import re
from .models import Article, SearchResult
import astrbot.api.message_components as Comp


def remove_images_from_content(content: str) -> str:
    """从 Markdown 内容中移除图片链接"""
    pattern = re.compile(r'!\[.*?\]\(https?://[^)]+\)\n?')
    return pattern.sub('', content)


def build_message_chain_from_markdown(content: str) -> list:
    """从 Markdown 内容构建消息链（保留图片位置）"""
    chain = []
    pattern = re.compile(r'!\[.*?\]\((https?://[^)]+)\)')

    last_end = 0
    for match in pattern.finditer(content):
        text_before = content[last_end:match.start()]
        if text_before:
            chain.append(Comp.Plain(text_before))

        img_url = match.group(1)
        chain.append(Comp.Image.fromURL(img_url))
        last_end = match.end()

    text_after = content[last_end:]
    if text_after:
        chain.append(Comp.Plain(text_after))

    return chain


def format_article_text(article: Article) -> str:
    """将文章转换为简洁的文本格式（不含图片）"""
    lines = [
        f"{article.title or '无标题'}\n\n",
        article.content or '无内容'
    ]
    return ''.join(lines)


def build_article_message(article: Article) -> tuple:
    """构建文章消息，返回 (text, chain)"""
    # Feed 类型：过滤 content 中的表情包，只保留 feed_images
    if article.article_type == 'feed':
        title = article.title or '无标题'
        clean_content = remove_images_from_content(article.content or '无内容')
        text = f"{title}\n\n{clean_content}"
        images = article.feed_images or []

        if not images:
            return text, []

        chain = [Comp.Plain(text), Comp.Plain("\n")]
        for img_url in images:
            chain.append(Comp.Image.fromURL(img_url))
        return None, chain

    # Discuss 类型：保留图片在文字中的原始位置
    title = article.title or '无标题'
    content = article.content or '无内容'
    full_content = f"{title}\n\n{content}"

    chain = build_message_chain_from_markdown(full_content)

    if not chain:
        return content, []

    return None, chain


def format_search_results(result: SearchResult, keyword: str, page: int,
                          tag_type: str = None, order: str = '') -> str:
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


def format_help_message() -> str:
    """格式化帮助信息"""
    from .constants import SEARCH_TAG_IDS

    tag_types = " | ".join(SEARCH_TAG_IDS.keys())
    return (
        "📖 牛客文章助手\n\n"
        "用法:\n"
        "牛客 <链接> - 解析文章\n"
        "牛客 <关键词> - 搜索文章\n"
        "牛客 <关键词> <筛选> - 筛选类型\n"
        "牛客 <关键词> 最新 - 最新排序\n\n"
        f"筛选类型: {tag_types}\n"
        "排序方式: 最新\n\n"
        "示例:\n"
        "牛客 https://www.nowcoder.com/discuss/123456\n"
        "牛客 阿里 面经\n"
        "牛客 字节 最新"
    )