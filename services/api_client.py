"""
API请求和页面抓取 - 异步版本
使用 aiohttp 并发请求、连接池复用、减少延迟
"""
import aiohttp
import asyncio
from urllib.parse import quote
from .parser import parse_feed_html, parse_discuss_api_data, parse_url_type, parse_search_html, parse_search_api_data
from .models import Article, SearchResult
from .constants import SEARCH_TAG_IDS
import re


# 延迟配置（秒）- 仅在必要时使用
DELAY_MIN, DELAY_MAX = 0.3, 0.8
DELAY_PAGE_MIN, DELAY_PAGE_MAX = 0.5, 1.0

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.nowcoder.com/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 预编译正则
RE_LOG_ID = re.compile(r'"logId":"([^"]+)"')
RE_SESSION_ID = re.compile(r'"sessionId":"([^"]+)"')
RE_INITIAL_STATE = re.compile(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>', re.DOTALL)

# 全局连接池
_global_session = None


async def get_session() -> aiohttp.ClientSession:
    """获取全局连接池"""
    global _global_session
    if _global_session is None or _global_session.closed:
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            enable_cleanup_closed=True,
            force_close=False
        )
        _global_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=10)
        )
    return _global_session


async def close_session():
    """关闭全局连接池"""
    global _global_session
    if _global_session and not _global_session.closed:
        await _global_session.close()
        _global_session = None


async def random_delay(min_delay=DELAY_MIN, max_delay=DELAY_MAX):
    """随机延迟"""
    delay = min_delay + (max_delay - min_delay) * (asyncio.get_event_loop().time() % 1)
    await asyncio.sleep(delay)


async def _request(session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> tuple:
    """统一请求方法，返回 (text, json_data)"""
    headers = {**DEFAULT_HEADERS, **kwargs.get('headers', {})}
    kwargs['headers'] = headers
    kwargs.setdefault('timeout', aiohttp.ClientTimeout(total=10))

    async with session.request(method, url, **kwargs) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return await resp.text(), await resp.json()
        return await resp.text(), None


def _check_api_response(data):
    """检查API响应"""
    if not data or not data.get('success'):
        raise Exception(data.get('msg', 'API返回错误') if data else 'API返回空数据')


async def fetch_feed_article(session: aiohttp.ClientSession, uuid: str) -> Article:
    """获取feed类型文章（并发请求）"""
    tdk_url = f"https://gw-c.nowcoder.com/api/sparta/content-terminal-tdk/moments?uuid={uuid}&t="
    page_url = f"https://www.nowcoder.com/feed/main/detail/{uuid}"

    tdk_task = _request(session, 'GET', tdk_url, headers={'Accept': 'application/json'})
    page_task = _request(session, 'GET', page_url)

    (_, tdk_data), (html, _) = await asyncio.gather(tdk_task, page_task)

    _check_api_response(tdk_data)

    data = parse_feed_html(html, uuid)
    data.update({
        'title': tdk_data['data'].get('title'),
        'keywords': tdk_data['data'].get('keywords'),
        'description': tdk_data['data'].get('description')
    })
    return Article(**data)


async def fetch_discuss_article(session: aiohttp.ClientSession, article_id: str) -> Article:
    """获取discuss类型文章"""
    api_url = f"https://gw-c.nowcoder.com/api/sparta/detail/content-data/detail/{article_id}"
    _, data = await _request(session, 'GET', api_url,
                              headers={'Origin': 'https://www.nowcoder.com'})
    _check_api_response(data)

    parsed = parse_discuss_api_data(data, article_id)
    parsed['title'] = data['data'].get('title')
    return Article(**parsed)


# 文章获取函数映射
FETCHERS = {'discuss': fetch_discuss_article, 'feed': fetch_feed_article}


async def fetch_article(url: str) -> Article:
    """根据URL类型获取文章"""
    url_type, article_id = parse_url_type(url)
    if url_type not in FETCHERS:
        raise ValueError(f"无法识别的URL格式: {url}")

    session = await get_session()
    return await FETCHERS[url_type](session, article_id)


async def fetch_articles(urls: list) -> list:
    """批量获取文章（并发）"""
    session = await get_session()

    tasks = []
    for url in urls:
        url_type, article_id = parse_url_type(url)
        if url_type in FETCHERS:
            tasks.append(FETCHERS[url_type](session, article_id))

    articles = await asyncio.gather(*tasks, return_exceptions=False)
    return articles


async def fetch_search_results(keyword: str, page: int = 1, log_id: str = None, session_id: str = None,
                                tag_type: str = None, order: str = '') -> SearchResult:
    """获取搜索结果"""
    tag_id = SEARCH_TAG_IDS.get(tag_type) if tag_type else None
    tag_param = []
    if tag_id is not None:
        tag_param = [{"name": tag_type, "id": tag_id, "count": None}]

    session = await get_session()

    if page == 1:
        url = f"https://www.nowcoder.com/search/all?query={quote(keyword)}"
        html, _ = await _request(session, 'GET', url, headers={'Accept': 'text/html'})
        result = parse_search_html(html, keyword, page)

        # 调试：输出第一条和第二条搜索结果的HTML片段
        print(f"\n=== DEBUG Search Results ===")
        print(f"Total items parsed: {len(result.items)}")
        if len(result.items) >= 2:
            print(f"Item 1: id={result.items[0].id}, type={result.items[0].article_type}, title={result.items[0].title}")
            print(f"Item 2: id={result.items[1].id}, type={result.items[1].article_type}, title={result.items[1].title}")

        match = RE_INITIAL_STATE.search(html)
        if match:
            state = match.group(1)
            log_match = RE_LOG_ID.search(state)
            session_match = RE_SESSION_ID.search(state)
            if log_match:
                result.log_id = log_match.group(1)
            if session_match:
                result.session_id = session_match.group(1)

        if not tag_param and not order:
            return result

        await random_delay()
        payload = {
            "type": "all", "query": keyword, "page": 1, "tag": tag_param, "order": order,
            "gioParams": {
                "logid_var": result.log_id or '', "sessionID_var": result.session_id or '',
                "searchFrom_var": "搜索页输入框", "searchEnter_var": "主站"
            }
        }
        _, data = await _request(session, 'POST', "https://gw-c.nowcoder.com/api/sparta/pc/search",
                                 json=payload, headers={'Content-Type': 'application/json'})
        _check_api_response(data)

        # 调试：输出API响应的前两条记录
        import logging
        records = data.get('data', {}).get('records', [])
        if len(records) > 1:
            logging.warning(f"DEBUG API Record 1 full data: {records[1]}")

        saved_log_id, saved_session_id = result.log_id, result.session_id
        result = parse_search_api_data(data, keyword, page)

        api_data = data.get('data', {})
        if not result.log_id:
            result.log_id = api_data.get('logId') or saved_log_id
        if not result.session_id:
            result.session_id = api_data.get('sessionId') or saved_session_id

        return result

    if not log_id or not session_id:
        raise ValueError("翻页需要log_id和session_id")

    payload = {
        "type": "all", "query": keyword, "page": page, "tag": tag_param, "order": order,
        "gioParams": {
            "logid_var": log_id, "sessionID_var": session_id,
            "searchFrom_var": "搜索页输入框", "searchEnter_var": "主站"
        }
    }
    _, data = await _request(session, 'POST', "https://gw-c.nowcoder.com/api/sparta/pc/search",
                             json=payload, headers={'Content-Type': 'application/json'})
    _check_api_response(data)

    result = parse_search_api_data(data, keyword, page)
    result.log_id, result.session_id = log_id, session_id
    return result


async def fetch_all_search_results(keyword: str, max_pages: int = 10, tag_type: str = None, order: str = '') -> list:
    """获取多页搜索结果"""
    results = []
    log_id, session_id = None, None

    for page in range(1, max_pages + 1):
        try:
            result = await fetch_search_results(keyword, page, log_id, session_id, tag_type, order)
            log_id, session_id = result.log_id, result.session_id
            results.append(result)

            if not result.items or page >= result.total_pages:
                break

            if page < max_pages:
                await random_delay(DELAY_PAGE_MIN, DELAY_PAGE_MAX)
        except Exception as e:
            raise Exception(f"获取第{page}页失败: {e}")

    return results