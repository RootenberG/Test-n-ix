import asyncio
import random
from enum import Enum
from typing import List, Optional, Any

import aiohttp
import typer
import pydantic
from bs4 import BeautifulSoup

app = typer.Typer()

REQUEST_TIMEOUT: int = 5
GH_LINK = "https://github.com/"


class SearchType(Enum):
    REPOSITORIES = "Repositories"
    ISSUES = "Issues"
    WIKIS = "Wikis"


class SearchResult(pydantic.BaseModel):
    link: str
    owner: Optional[str] = None
    language_stats: Any


class GitHubCrawler:
    def __init__(
        self,
        search_keywords: List[str],
        proxies: List[str],
        search_type: SearchType = SearchType.REPOSITORIES,
    ):
        self.search_keywords = search_keywords
        self.proxies = proxies
        self.search_type = search_type

    def _get_random_proxy(self, proxies: List[str] = None) -> str:
        if proxies is None:
            proxies = self.proxies
        return random.choice(proxies)

    def _get_search_url(self) -> str:
        base_url = "https://github.com/search?q="
        query = "+".join(self.search_keywords)
        return f"{base_url}{query}&type={self.search_type.value}"

    async def fetch_with_proxy(
        self, *, session: aiohttp.ClientSession, url: str, proxy: str
    ):
        try:
            async with session.get(
                url, proxy=proxy, timeout=REQUEST_TIMEOUT
            ) as response:
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Error: {e}")
            return None

    async def fetch_search_results(self) -> List[SearchResult]:
        url = self._get_search_url()

        async with aiohttp.ClientSession() as session:
            html = None
            remaining_proxies = self.proxies.copy()

            while html is None and remaining_proxies:
                proxy = self._get_random_proxy(remaining_proxies)
                print(f"Trying proxy {proxy}")
                remaining_proxies.remove(proxy)
                print(f"Remaining proxies: {remaining_proxies}")
                html = await self.fetch_with_proxy(
                    session=session, url=url, proxy=proxy
                )

            if not html:
                raise SystemExit("All proxies failed")

        soup = BeautifulSoup(html, "html.parser")
        if not self.search_type == SearchType.REPOSITORIES:
            return [
                SearchResult(link=GH_LINK + a["href"])
                for a in soup.select(".f4.text-normal a")
            ]
        if self.search_type == SearchType.REPOSITORIES:
            results = soup.select(".repo-list-item")
            return [
                SearchResult.parse_obj(
                    {
                        "link": GH_LINK + link["href"],
                        "owner": link["href"].split("/")[1],
                        "language_stats": {
                            "language": item.select_one(
                                'span[itemprop="programmingLanguage"]'
                            ).text
                            if item.select_one('span[itemprop="programmingLanguage"]')
                            else None,
                        },
                    }
                )
                for item in results
                if (link := item.select_one("a.v-align-middle")) is not None
            ]


@app.command(help="Search GitHub for repositories, issues, or wikis")
def main(
    search_keywords: str = "python",
    search_type: SearchType = SearchType.WIKIS.value,
    proxies: List[str] = None,
):
    search_keywords = search_keywords.split(",")
    crawler = GitHubCrawler(search_keywords, proxies, SearchType(search_type))
    results = asyncio.run(crawler.fetch_search_results())
    for result in results:
        typer.echo(f"Link: {result.link}")
        if result.owner is not None:
            typer.echo(f"Owner: {result.owner}")
            if result.language_stats is not None:
                typer.echo("Language Stats:")
                for lang, stat in result.language_stats.items():
                    typer.echo(f"    {lang}: {stat}")
        typer.echo("")


if __name__ == "__main__":
    app()
