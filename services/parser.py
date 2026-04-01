"""
HTML解析和数据提取
"""
import re
import json
from html.parser import HTMLParser
from .models import Article, SearchResultItem, SearchResult
from urllib.parse import unquote


# 预编译正则
RE_URL_DISCUSS = re.compile(r'/discuss/(\d+)')
RE_URL_FEED = re.compile(r'/feed/main/detail/([a-f0-9]+)')
RE_FEED_CONTENT = re.compile(r'<div class="feed-content-text[^"]*"[^>]*>(.*?)</div>', re.DOTALL)
RE_FEED_IMG = re.compile(r'"imgMoment":\s*(\[[^\]]+\])')
RE_FEED_AUTHOR = re.compile(r'class="name-text[^>]*>([^<]+)<')
RE_FEED_TIME = re.compile(r'class="time-text[^>]*>([^<]+)<')
RE_FEED_JOB = re.compile(r'class="job-text[^>]*>([^<]+)<')
RE_FEED_VIEW = re.compile(r'浏览\s*(\d+)')
RE_FEED_LIKE = re.compile(r'(\d+)\s*分享')
RE_FEED_COMMENT = re.compile(r'评论\s*\((\d+)\)')
RE_PAGER = re.compile(r'<ul class="pager"[^>]*>.*?</ul>', re.DOTALL)
RE_PAGE_NUM = re.compile(r'<li[^>]*>(\d+)</li>')
RE_NEWLINES = re.compile(r'\n{3,}')


class HTMLToTextExtractor(HTMLParser):
    """从HTML提取纯文本"""

    def __init__(self):
        super().__init__()
        self._text = []
        self._tag = None
        self._list_type = None
        self._list_num = 0

    def handle_starttag(self, tag, attrs):
        self._tag = tag
        actions = {
            'h1': '\n\n## ', 'h2': '\n\n## ', 'h3': '\n\n## ',
            'p': '\n\n', 'br': '\n', 'pre': '\n```\n',
            'strong': '**', 'b': '**', 'em': '*', 'i': '*',
        }
        if tag in actions:
            self._text.append(actions[tag])
        elif tag == 'code' and self._tag != 'pre':
            self._text.append('`')
        elif tag == 'img':
            src = next((v for a, v in attrs if a == 'src'), None)
            if src:
                self._text.append(f'\n![图片]({src})\n')
        elif tag in ('ol', 'ul'):
            self._list_type, self._list_num = tag, 0
            self._text.append('\n')
        elif tag == 'li':
            if self._list_type == 'ol':
                self._list_num += 1
                self._text.append(f'\n{self._list_num}. ')
            else:
                self._text.append('\n- ')

    def handle_endtag(self, tag):
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'):
            self._text.append('\n')
        elif tag == 'pre':
            self._text.append('\n```\n')
        elif tag == 'code' and self._tag != 'pre':
            self._text.append('`')
        elif tag in ('strong', 'b'):
            self._text.append('**')
        elif tag in ('em', 'i'):
            self._text.append('*')
        elif tag in ('ol', 'ul'):
            self._list_type = None
            self._text.append('\n')
        self._tag = None

    def handle_data(self, data):
        self._text.append(data)

    def get_text(self):
        return RE_NEWLINES.sub('\n\n', ''.join(self._text)).strip()


def extract_text_from_html(html: str) -> str:
    """从HTML提取纯文本"""
    extractor = HTMLToTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def parse_url_type(url: str) -> tuple:
    """判断URL类型并提取ID"""
    m = RE_URL_DISCUSS.search(url)
    if m:
        return ('discuss', m.group(1))
    m = RE_URL_FEED.search(url)
    if m:
        return ('feed', m.group(1))
    return (None, None)


def _safe_int(match, default=0):
    """安全提取整数"""
    return int(match.group(1)) if match else default


def parse_feed_html(html: str, uuid: str) -> dict:
    """从feed类型HTML提取数据"""
    content_m = RE_FEED_CONTENT.search(html)
    rich = content_m.group(1) if content_m else ''

    images = []
    img_m = RE_FEED_IMG.search(html)
    if img_m:
        try:
            images = [i.get('src', '') for i in json.loads(img_m.group(1)) if i.get('src')]
        except:
            pass

    return {
        'id': uuid,
        'author': (RE_FEED_AUTHOR.search(html) or ['', ''])[1],
        'identity': (RE_FEED_JOB.search(html) or ['', ''])[1],
        'post_time': (RE_FEED_TIME.search(html) or ['', ''])[1],
        'rich_content': rich,
        'content': extract_text_from_html(rich),
        'feed_images': images,
        'view_count': _safe_int(RE_FEED_VIEW.search(html)),
        'like_count': _safe_int(RE_FEED_LIKE.search(html)),
        'comment_count': _safe_int(RE_FEED_COMMENT.search(html)),
        'url': f"https://www.nowcoder.com/feed/main/detail/{uuid}",
        'article_type': 'feed'
    }


def parse_discuss_api_data(data: dict, article_id: str) -> dict:
    """从discuss类型API响应提取数据"""
    d = data.get('data', {})
    user = d.get('userBrief', {})

    return {
        'id': d.get('id'),
        'author': user.get('nickname'),
        'author_id': d.get('authorId'),
        'education': user.get('educationInfo'),
        'identity': user.get('authDisplayInfo'),
        'post_time': d.get('postTime'),
        'rich_content': d.get('richText'),
        'content': extract_text_from_html(d.get('richText', '')),
        'view_count': d.get('viewCount', 0),
        'like_count': d.get('likeCount', 0),
        'comment_count': d.get('commentCount', 0),
        'url': f"https://www.nowcoder.com/discuss/{article_id}",
        'article_type': 'discuss'
    }


def parse_search_html(html: str, keyword: str, page: int) -> SearchResult:
    """从搜索页面HTML提取结果"""
    items = []

    # 提取feed文章
    for uuid in set(RE_URL_FEED.findall(html)):
        title_m = re.search(rf'/feed/main/detail/{uuid}[^>]*>([^<]+)<', html)
        items.append(SearchResultItem(
            id=uuid, title=(title_m.group(1).strip() if title_m else f'Feed-{uuid[:8]}'),
            url='', article_type='feed'
        ))

    # 提取discuss文章
    for aid in set(RE_URL_DISCUSS.findall(html)):
        title_m = re.search(rf'/discuss/{aid}[^>]*>([^<]+)<', html)
        items.append(SearchResultItem(
            id=aid, title=(title_m.group(1).strip() if title_m else f'Discuss-{aid}'),
            url='', article_type='discuss'
        ))

    # 总页数
    pager_m = RE_PAGER.search(html)
    pages = max(map(int, RE_PAGE_NUM.findall(pager_m.group(0))), default=0) if pager_m else 0

    return SearchResult(keyword=unquote(keyword), page=page, items=items, total_pages=pages)


def parse_search_api_data(data: dict, keyword: str, page: int) -> SearchResult:
    """从搜索API响应提取结果"""
    items = []
    for r in data.get('data', {}).get('records', []):
        if not isinstance(r, dict):
            continue
        rd = r.get('data', {})
        if not isinstance(rd, dict):
            continue

        # 按优先级提取数据，确保每个候选都是字典
        candidates = [rd.get('momentData'), rd.get('subjectData'), rd.get('contentData')]
        src = next((c for c in candidates if isinstance(c, dict) and c), None)
        if not src:
            continue

        item_id = src.get('uuid') or str(src.get('id', '')) or str(rd.get('contentId', ''))
        if not item_id:
            continue

        article_type = 'feed' if src.get('uuid') else 'discuss'
        items.append(SearchResultItem(
            id=str(item_id), title=src.get('title') or f'文章-{item_id[:8]}',
            url='', article_type=article_type
        ))

    total = data.get('data', {}).get('total', 0)
    pages = data.get('data', {}).get('totalPage', 0) or ((total + 19) // 20 if total else 0)

    return SearchResult(keyword=keyword, page=page, items=items, total_pages=pages)