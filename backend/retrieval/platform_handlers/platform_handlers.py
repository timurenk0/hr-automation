from dataclasses import dataclass
from platform_handlers.github_handler import fetch_profile_data
import requests


async def github_handler(url: str, is_repo: bool):
    API_URL = "https://api.github.com"

    username = url.split("/")[3]

    if not username:
        print("[ERROR] Corrupt Github URL (no username found)")
        return

    if is_repo:
        repo_name = url.split("/")[4]

        repo_response = requests.get(f"{API_URL}/repos/{username}/{repo_name}")
        return repo_response

    user_response = await fetch_profile_data(username)
    return user_response


def linkedin_handler():
    pass


PLATFORM_HANDLERS = {"github": github_handler, "linked": linkedin_handler}
