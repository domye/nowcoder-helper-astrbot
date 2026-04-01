"""
API请求和页面抓取
"""
import requests
import re
import time
import random
from urllib.parse import quote
from parser import parse_feed_html, parse_discuss_api_data, parse_url_type, parse_search_html, parse_search_api_data
from models import Article, SearchResult


# 延迟配置（秒）
DELAY_MIN, DELAY_MAX = 0.5, 1.5
DELAY_PAGE_MIN, DELAY_PAGE_MAX = 1.0, 2.0

# 搜索筛选类型TAG ID配置
SEARCH_TAG_IDS = {
    '全部': None,      # 不传tag参数
    '面经': 818,
    '求职进度': 861,
    '内推': 823,
    '公司评价': 856,
}

# 排序方式配置
SEARCH_ORDER_TYPES = {
    '默认': '',        # 空字符串
    '最新': 'create',
}

# 会话复用
SESSION = requests.Session()

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


def random_delay(min_delay=DELAY_MIN, max_delay=DELAY_MAX):
    """随机延迟"""
    time.sleep(random.uniform(min_delay, max_delay))


def _request(method, url, **kwargs):
    """统一请求方法"""
    kwargs.setdefault('headers', DEFAULT_HEADERS)
    kwargs.setdefault('timeout', 15)
    resp = SESSION.request(method, url, **kwargs)
    resp.raise_for_status()
    return resp


def _check_api_response(data):
    """检查API响应"""
    if not data.get('success'):
        raise Exception(data.get('msg', 'API返回错误'))


def fetch_feed_article(uuid: str) -> Article:
    """获取feed类型文章"""
    tdk_url = f"https://gw-c.nowcoder.com/api/sparta/content-terminal-tdk/moments?uuid={uuid}&t="
    resp = _request('GET', tdk_url, headers={**DEFAULT_HEADERS, 'Accept': 'application/json'})
    tdk_data = resp.json()
    _check_api_response(tdk_data)

    random_delay()

    page_url = f"https://www.nowcoder.com/feed/main/detail/{uuid}"
    resp = _request('GET', page_url)

    data = parse_feed_html(resp.text, uuid)
    data.update({
        'title': tdk_data['data'].get('title'),
        'keywords': tdk_data['data'].get('keywords'),
        'description': tdk_data['data'].get('description')
    })
    return Article(**data)


def fetch_discuss_article(article_id: str) -> Article:
    """获取discuss类型文章"""
    api_url = f"https://gw-c.nowcoder.com/api/sparta/detail/content-data/detail/{article_id}"
    resp = _request('GET', api_url, headers={**DEFAULT_HEADERS, 'Origin': 'https://www.nowcoder.com'})
    data = resp.json()
    _check_api_response(data)

    parsed = parse_discuss_api_data(data, article_id)
    parsed['title'] = data['data'].get('title')
    random_delay()
    return Article(**parsed)


# 文章获取函数映射
FETCHERS = {'discuss': fetch_discuss_article, 'feed': fetch_feed_article}


def fetch_article(url: str) -> Article:
    """根据URL类型获取文章"""
    url_type, article_id = parse_url_type(url)
    if url_type not in FETCHERS:
        raise ValueError(f"无法识别的URL格式: {url}")
    return FETCHERS[url_type](article_id)


def fetch_articles(urls: list) -> list:
    """批量获取文章"""
    articles, total = [], len(urls)
    for i, url in enumerate(urls, 1):
        try:
            articles.append(fetch_article(url))
            if i < total:
                random_delay()
        except Exception as e:
            raise Exception(f"获取文章失败 {url}: {e}")
    return articles


def fetch_search_results(keyword: str, page: int = 1, log_id: str = None, session_id: str = None,
                         tag_type: str = None, order: str = '') -> SearchResult:
    """获取搜索结果

    Args:
        keyword: 搜索关键词
        page: 页码
        log_id: 翻页需要的log_id
        session_id: 翻页需要的session_id
        tag_type: 筛选类型，可选值: '全部', '面经', '求职进度', '内推', '公司评价'
        order: 排序方式，可选值: ''(默认), 'create'(最新)
    """
    # 构建tag参数
    tag_id = SEARCH_TAG_IDS.get(tag_type) if tag_type else None
    tag_param = []
    if tag_id is not None:
        tag_param = [{"name": tag_type, "id": tag_id, "count": None}]

    if page == 1:
        url = f"https://www.nowcoder.com/search/all?query={quote(keyword)}"
        resp = _request('GET', url, headers={**DEFAULT_HEADERS, 'Accept': 'text/html'})
        result = parse_search_html(resp.text, keyword, page)

        match = RE_INITIAL_STATE.search(resp.text)
        if match:
            state = match.group(1)
            result.log_id = (RE_LOG_ID.search(state) or ['', ''])[1]
            result.session_id = (RE_SESSION_ID.search(state) or ['', ''])[1]

        # 如果有筛选条件，第一页也需要通过API请求
        if tag_param or order:
            random_delay()
            payload = {
                "type": "all", "query": keyword, "page": 1, "tag": tag_param, "order": order,
                "gioParams": {
                    "logid_var": result.log_id or '', "sessionID_var": result.session_id or '',
                    "searchFrom_var": "搜索页输入框", "searchEnter_var": "主站"
                }
            }
            resp = _request('POST', "https://gw-c.nowcoder.com/api/sparta/pc/search",
                            json=payload, headers={**DEFAULT_HEADERS, 'Content-Type': 'application/json'})
            data = resp.json()
            _check_api_response(data)
            result = parse_search_api_data(data, keyword, page)
            result.log_id = result.log_id
            result.session_id = result.session_id

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
    resp = _request('POST', "https://gw-c.nowcoder.com/api/sparta/pc/search",
                    json=payload, headers={**DEFAULT_HEADERS, 'Content-Type': 'application/json'})
    data = resp.json()
    _check_api_response(data)

    result = parse_search_api_data(data, keyword, page)
    result.log_id, result.session_id = log_id, session_id
    return result


def fetch_all_search_results(keyword: str, max_pages: int = 10, tag_type: str = None, order: str = '') -> list:
    """获取多页搜索结果

    Args:
        keyword: 搜索关键词
        max_pages: 最大页数
        tag_type: 筛选类型，可选值: '全部', '面经', '求职进度', '内推', '公司评价'
        order: 排序方式，可选值: ''(默认), 'create'(最新)
    """
    results, log_id, session_id = [], None, None

    for page in range(1, max_pages + 1):
        try:
            result = fetch_search_results(keyword, page, log_id, session_id, tag_type, order)
            log_id, session_id = result.log_id, result.session_id
            results.append(result)

            if not result.items:
                break

            if page >= result.total_pages:
                break

            if page < max_pages:
                random_delay(DELAY_PAGE_MIN, DELAY_PAGE_MAX)
        except Exception as e:
            raise Exception(f"获取第{page}页失败: {e}")

    return results