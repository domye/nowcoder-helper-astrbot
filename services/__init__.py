"""
Services 模块
"""
from .models import Article, SearchResult, SearchResultItem
from .constants import RE_NOWCODER_URL, SEARCH_TAG_IDS, SEARCH_ORDER_TYPES
from .session_manager import SessionManager, SearchSession
from .formatter import (
    build_article_message,
    format_article_text,
    format_search_results,
    format_help_message
)
from .api_client import (
    fetch_article,
    fetch_articles,
    fetch_search_results,
    fetch_all_search_results,
    close_session
)

__all__ = [
    # Models
    'Article', 'SearchResultItem', 'SearchResult',
    # Constants
    'RE_NOWCODER_URL', 'SEARCH_TAG_IDS', 'SEARCH_ORDER_TYPES',
    # Session
    'SessionManager', 'SearchSession',
    # Formatter
    'build_article_message', 'format_article_text', 'format_search_results', 'format_help_message',
    # API
    'fetch_article', 'fetch_articles', 'fetch_search_results', 'fetch_all_search_results', 'close_session'
]