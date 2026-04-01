"""
常量配置
"""
import re

# URL 正则
RE_NOWCODER_URL = re.compile(r'https?://www\.nowcoder\.com/(discuss/\d+|feed/main/detail/[a-f0-9]+)')

# 搜索筛选类型TAG ID配置
SEARCH_TAG_IDS = {
    '全部': None,
    '面经': 818,
    '求职进度': 861,
    '内推': 823,
    '公司评价': 856,
}

# 排序方式配置
SEARCH_ORDER_TYPES = {
    '默认': '',
    '最新': 'create',
}