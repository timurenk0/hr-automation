from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

from scrapling.fetchers import Fetcher


TARGET_URL = "https://quotes.toscrape.com/"
OUTPUT_PATH = Path("data/raw/quotes.jsonl")


# The workflow of Scrapling: 
# Python -> Scrapling Fetcher -> Http request 
# -> server -> HTML response -> Scrapling response


@dataclass(frozen=True, slots=True)
class RawDocument:
    source: str
    source_id: str
    url: str
    title: str | None
    content: str
    scraped_at: str
    metadata: dict


def make_source_id(source: str, content: str) -> str:
    value = f"{source}:{content}".encode("utf-8")
    return sha256(value).hexdigest()


# Data structure of page. (it isnt just a html)
# page.status
# page.headers
# page.cookies
# page.body
# page.url

def scrape() -> list[RawDocument]:
    page = Fetcher.get(
        TARGET_URL,
        impersonate="chrome",
    ) 

    if page.status >= 400:
        raise RuntimeError(
            f"Request failed with status {page.status}"
        )

    documents: list[RawDocument] = []

    # html document -> find every <div class ="quote"> -> Selectors
    # and inside each quote: span.text::text

    # Scrapling uses Scrapy/Parsel-style pseudo-selectors such as:
    # ::text, ::attr(href)

    for quote in page.css("div.quote"): 
        text = quote.css("span.text::text").get("") 
        author = quote.css("small.author::text").get("")
        tags = quote.css("a.tag::text").getall()

        text = text.strip()
        author = author.strip()

        if not text:
            continue

        document = RawDocument(
            source="quotes.toscrape",
            source_id=make_source_id(
                "quotes.toscrape",
                text,
            ),
            url=TARGET_URL,
            title=f"Quote by {author}" if author else None,
            content=text,
            scraped_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "author": author,
                "tags": list(tags),
            },
        )

        documents.append(document)

    return documents


def save_documents(documents: list[RawDocument]) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        for document in documents:
            json.dump(
                asdict(document),
                file,
                ensure_ascii=False,
            )
            file.write("\n")


if __name__ == "__main__":
    documents = scrape()
    save_documents(documents)

    print(f"Scraped {len(documents)} documents.")
    print(f"Saved to {OUTPUT_PATH}")