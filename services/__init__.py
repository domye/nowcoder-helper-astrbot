"""
Nowcoder helper services package
"""
from .api_client_async import fetch_article, fetch_articles, fetch_search_results, fetch_all_search_results
from .models import Article, SearchResultItem, SearchResult
from .parser import extract_text_from_html, parse_url_type

__all__ = [
    'fetch_article', 'fetch_articles', 'fetch_search_results', 'fetch_all_search_results',
    'Article', 'SearchResultItem', 'SearchResult',
    'extract_text_from_html', 'parse_url_type'
]