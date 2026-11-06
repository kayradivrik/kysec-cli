import html
import re
import urllib.parse
import requests

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)


def _clean_ddg_url(raw_url: str) -> str:
    if "uddg=" in raw_url:
        parsed = urllib.parse.urlparse(raw_url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return urllib.parse.unquote(qs["uddg"][0])
    return raw_url


def search_web_duckduckgo(query: str, max_results: int = 6) -> list[dict[str, str]]:
    """DuckDuckGo HTML uzerinden ucretsiz ve API anahtarsiz canli web aramasi yapar."""
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query.strip()},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except requests.RequestException:
        return []

    links = re.findall(
        r'class="result__a"[^>]* href="([^"]+)"[^>]*>(.*?)</a>',
        resp.text,
        re.DOTALL,
    )
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</a>',
        resp.text,
        re.DOTALL,
    )

    results: list[dict[str, str]] = []
    for (href, raw_title), raw_snip in list(zip(links, snippets))[:max_results]:
        title = html.unescape(re.sub(r"<[^<]+?>", "", raw_title)).strip()
        snippet = html.unescape(re.sub(r"<[^<]+?>", "", raw_snip)).strip()
        clean_url = _clean_ddg_url(html.unescape(href).strip())
        if title and snippet:
            results.append(
                {
                    "title": title,
                    "url": clean_url,
                    "snippet": snippet,
                }
            )
    return results


def format_web_results(query: str, max_results: int = 6) -> str:
    items = search_web_duckduckgo(query=query, max_results=max_results)
    if not items:
        return f"'{query}' icin web sonucu bulunamadi."

    lines = [f"[CANLI WEB ARAMA SONUCLARI ('{query}')]:"]
    for idx, item in enumerate(items, start=1):
        lines.append(
            f"{idx}. Baslik: {item['title']}\n"
            f"   URL: {item['url']}\n"
            f"   Ozet: {item['snippet']}"
        )
    return "\n\n".join(lines)

