import re
import requests
from django.core.cache import cache

API_BASE = "https://api.github.com"
TIMEOUT = 5  # seconds. Never call an API without a timeout.
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "django-github-viewer",   # GitHub requires a User-Agent
}

# GitHub usernames: letters, digits, single hyphens, max 39 chars
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


# ---- Custom exceptions: views catch these instead of raw requests errors ----
class GitHubError(Exception):
    """Base class for all GitHub related problems."""


class UserNotFound(GitHubError):
    pass


class RateLimited(GitHubError):
    pass


class GitHubUnavailable(GitHubError):
    pass


def _get(path, params=None):
    """Call the GitHub API and return parsed JSON, or raise a GitHubError."""
    url = f"{API_BASE}{path}"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        raise GitHubUnavailable("GitHub took too long to respond. Try again.")
    except requests.exceptions.RequestException:
        raise GitHubUnavailable("Could not connect to GitHub. Check your internet.")

    if response.status_code == 404:
        raise UserNotFound("No GitHub user with that username.")

    if response.status_code in (403, 429):
        if response.headers.get("X-RateLimit-Remaining") == "0":
            raise RateLimited("GitHub rate limit reached. Try again in a few minutes.")
        raise GitHubUnavailable("GitHub refused the request.")

    if response.status_code != 200:
        raise GitHubUnavailable(f"GitHub returned an error ({response.status_code}).")

    try:
        return response.json()
    except ValueError:
        raise GitHubUnavailable("GitHub sent an invalid response.")


def get_user(username):
    """Return a clean dict of profile data. Keys match BookmarkedProfile fields."""
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise UserNotFound("That is not a valid GitHub username.")

    cache_key = f"gh_user_{username.lower()}"
    data = cache.get(cache_key)
    if data is None:
        raw_data = _get(f"/users/{username}")
        data = {
            "username": raw_data["login"],              # correct capitalisation from GitHub
            "name": raw_data.get("name") or "",         # may be null
            "avatar_url": raw_data.get("avatar_url", ""),
            "bio": raw_data.get("bio") or "",           # may be null
            "public_repos": raw_data.get("public_repos", 0),
            "followers": raw_data.get("followers", 0),
            "following": raw_data.get("following", 0),
            "html_url": raw_data.get("html_url", ""),
        }
        cache.set(cache_key, data, 300)
    return data


def get_repos(username, limit=10):
    """Return the most recently updated public repos as a list of dicts."""
    username = (username or "").strip()
    cache_key = f"gh_repos_{username.lower()}_{limit}"
    data = cache.get(cache_key)
    if data is None:
        raw_data = _get(
            f"/users/{username}/repos",
            params={"sort": "updated", "direction": "desc", "per_page": limit},
        )
        data = [
            {
                "name": repo["name"],
                "description": repo.get("description") or "",
                "language": repo.get("language") or "n/a",
                "stars": repo.get("stargazers_count", 0),
                "html_url": repo.get("html_url", ""),
            }
            for repo in raw_data
        ]
        cache.set(cache_key, data, 300)  # 300 seconds cache bonus
    return data
