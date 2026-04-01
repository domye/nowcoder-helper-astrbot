"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Article:
    """文章数据模型"""
    id: str
    title: str
    author: str
    content: str
    url: str
    post_time: Optional[str] = None
    identity: Optional[str] = None
    rich_content: Optional[str] = None
    feed_images: List[str] = field(default_factory=list)
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    keywords: Optional[str] = None
    description: Optional[str] = None
    author_id: Optional[str] = None
    education: Optional[str] = None
    article_type: str = 'unknown'


@dataclass
class SearchResultItem:
    """搜索结果项"""
    id: str
    title: str
    url: str
    article_type: str
    snippet: Optional[str] = None

    def to_url(self) -> str:
        """生成完整URL"""
        base = "https://www.nowcoder.com"
        return f"{base}/feed/main/detail/{self.id}" if self.article_type == 'feed' else f"{base}/discuss/{self.id}"


@dataclass
class SearchResult:
    """搜索结果"""
    keyword: str
    page: int
    items: List[SearchResultItem] = field(default_factory=list)
    total_pages: int = 0
    log_id: Optional[str] = None
    session_id: Optional[str] = None