from dataclasses import dataclass
from platform_handlers.github_handler import fetch_profile, fetch_repo
import requests


async def github_handler(url: str, is_repo: bool):
    username = url.split("/")[3]

    if not username:
        print("[ERROR] Corrupt Github URL (no username found)")

        return

    if is_repo:
        repo_name = url.split("/")[4]

        repo_response = await fetch_repo(username, repo_name)

        return repo_response

    user_response = await fetch_profile(username)

    return user_response


def linkedin_handler():
    pass


PLATFORM_HANDLERS = {"github": github_handler, "linked": linkedin_handler}
