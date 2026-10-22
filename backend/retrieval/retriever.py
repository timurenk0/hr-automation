from platform_handlers.platform_handlers import PLATFORM_HANDLERS
from urllib.parse import urlparse
import asyncio


async def scrape_url(urls: list[str]):
    for url in urls:
        hostname = urlparse(url).hostname.split(".")[0]

        print(hostname)

        match hostname:
            case "github":
                link_parts = url.split("/")

                is_repo = False

                if len(link_parts) > 4:
                    is_repo = True

                handler = PLATFORM_HANDLERS["github"]
                github_data = await handler(url, is_repo)

                return github_data

    return "Not github link"


def main():
    result = asyncio.run(scrape_url(["https://github.com/timurenk0/spektr-cmms"]))
    print(result)


if __name__ == "__main__":
    main()
