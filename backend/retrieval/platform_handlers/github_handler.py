import requests

API_URL = "https://api.github.com"


async def fetch_profile(username: str):
    profile_response = requests.get(f"{API_URL}/users/{username}")
    profile_response.raise_for_status()

    profile_response = profile_response.json()
    profile_data = {
        "username": profile_response["login"],
        "bio": profile_response["bio"],
        "followers": profile_response["followers"],
    }

    repos_response = requests.get(f"{API_URL}/users/{username}/repos")
    repos_response.raise_for_status()
    repos_response = repos_response.json()

    repos_data = [
        {
            "name": repo["name"],
            "description": repo["description"] or None,
            "stars": repo["stargazers_count"],
            "language": repo["language"],
            "topics": repo["topics"] or None,
        }
        for repo in repos_response
    ]

    return {"user": profile_data, "repos": repos_data}


async def fetch_repo(username: str, repo_name: str):
    repo_response = requests.get(f"{API_URL}/repos/{username}/{repo_name}")
    repo_response.raise_for_status()
    repo_response = repo_response.json()

    repo_languages_response = requests.get(
        f"{API_URL}/repos/{username}/{repo_name}/languages"
    )
    repo_languages_response.raise_for_status()
    repo_languages_data = repo_languages_response.json()

    return {"languages": repo_languages_data, "topics": repo_response["topics"] or None}
