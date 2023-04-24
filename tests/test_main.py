import pytest
from typing import List
from unittest.mock import AsyncMock

from main import GitHubCrawler

REQUEST_TIMEOUT = 5


@pytest.fixture
def search_keywords() -> List[str]:
    return "python,asyncio"


@pytest.fixture
def proxies() -> List[str]:
    return ["http://proxy1.com", "http://proxy2.com"]


@pytest.fixture
def mock_response():
    response = AsyncMock()
    response.text = "html"
    return response


def test_get_random_proxy(proxies):
    crawler = GitHubCrawler([], proxies)
    result = crawler._get_random_proxy()
    assert result in proxies


def test_get_search_url(search_keywords):
    search_keywords = search_keywords.split(",")
    crawler = GitHubCrawler(search_keywords, [])
    expected_url = "https://github.com/search?q=python+asyncio&type=Repositories"
    print(crawler._get_search_url(), expected_url)
    assert crawler._get_search_url() == expected_url
