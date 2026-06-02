#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
START_MARKER = "<!-- merged-contributions:start -->"
END_MARKER = "<!-- merged-contributions:end -->"
EMPTY_MESSAGE = "_아직 자동으로 수집된 외부 오픈소스 merge 기록이 없습니다._"


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default

    try:
        return int(raw)
    except ValueError:
        return default


def split_csv(value: str | None) -> set[str]:
    if not value:
        return set()

    return {part.strip().lower() for part in value.split(",") if part.strip()}


def request_json(url: str, token: str | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "JetProc-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {error.code} {detail}") from error
    except URLError as error:
        raise RuntimeError(f"GitHub API request failed: {error}") from error


def search_merged_pull_requests(
    username: str,
    excluded_owners: set[str],
    fetch_limit: int,
    token: str | None,
) -> list[dict[str, Any]]:
    exclusions = " ".join(f"-user:{owner}" for owner in sorted(excluded_owners))
    query = f"is:pr is:merged author:{username} archived:false {exclusions}".strip()
    params = urlencode(
        {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(fetch_limit, 100),
        }
    )
    payload = request_json(f"{API_ROOT}/search/issues?{params}", token)
    return payload.get("items", [])


def load_pull_request_details(item: dict[str, Any], token: str | None) -> dict[str, Any] | None:
    pull_request = item.get("pull_request") or {}
    api_url = pull_request.get("url")
    if not api_url:
        return None

    return request_json(api_url, token)


def owner_from_full_name(full_name: str) -> str:
    return full_name.split("/", 1)[0].lower()


def normalize_pull_requests(
    items: list[dict[str, Any]],
    username: str,
    excluded_owners: set[str],
    max_items: int,
    token: str | None,
) -> list[dict[str, str]]:
    username_lower = username.lower()
    seen_urls: set[str] = set()
    rows: list[dict[str, str]] = []

    for item in items:
        if len(rows) >= max_items:
            break

        details = load_pull_request_details(item, token)
        if not details or not details.get("merged_at"):
            continue

        repo = ((details.get("base") or {}).get("repo") or {})
        repo_full_name = repo.get("full_name")
        repo_url = repo.get("html_url")
        if not repo_full_name or not repo_url:
            continue

        owner = owner_from_full_name(repo_full_name)
        if owner == username_lower or owner in excluded_owners:
            continue
        if repo.get("private") or repo.get("archived"):
            continue

        html_url = details.get("html_url")
        if not html_url or html_url in seen_urls:
            continue

        seen_urls.add(html_url)
        rows.append(
            {
                "merged_at": details["merged_at"],
                "repo": repo_full_name,
                "repo_url": repo_url,
                "number": str(details.get("number") or item.get("number") or ""),
                "title": details.get("title") or item.get("title") or "Merged pull request",
                "url": html_url,
            }
        )

    rows.sort(key=lambda row: row["merged_at"], reverse=True)
    return rows


def escape_markdown(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("\n", " ")
        .strip()
    )


def format_date(value: str) -> str:
    merged_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return merged_at.astimezone(timezone.utc).strftime("%Y-%m-%d")


def render_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return EMPTY_MESSAGE

    lines = [
        "| Merged | Repository | Pull Request |",
        "|:---:|:---|:---|",
    ]

    for row in rows:
        title = escape_markdown(row["title"])
        repo = escape_markdown(row["repo"])
        number = escape_markdown(row["number"])
        lines.append(
            f"| {format_date(row['merged_at'])} | [{repo}]({row['repo_url']}) | "
            f"[#{number} {title}]({row['url']}) |"
        )

    return "\n".join(lines)


def replace_marker_block(readme: str, rendered: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{rendered}\n{END_MARKER}"

    if not pattern.search(readme):
        raise RuntimeError(
            f"README is missing the contribution markers: {START_MARKER} / {END_MARKER}"
        )

    return pattern.sub(replacement, readme, count=1)


def main() -> int:
    username = os.environ.get("GITHUB_USERNAME")
    if not username:
        raise RuntimeError("GITHUB_USERNAME is required.")

    readme_path = Path(os.environ.get("README_PATH", "README.md"))
    max_items = env_int("MAX_ITEMS", 12)
    fetch_limit = env_int("FETCH_LIMIT", max(max_items * 4, 40))
    excluded_owners = split_csv(os.environ.get("EXCLUDED_OWNERS"))
    excluded_owners.add(username.lower())
    token = os.environ.get("CONTRIBUTIONS_TOKEN") or os.environ.get("GITHUB_TOKEN")

    items = search_merged_pull_requests(username, excluded_owners, fetch_limit, token)
    rows = normalize_pull_requests(items, username, excluded_owners, max_items, token)

    readme = readme_path.read_text(encoding="utf-8")
    updated = replace_marker_block(readme, render_rows(rows))
    readme_path.write_text(updated, encoding="utf-8")

    print(f"Updated {readme_path} with {len(rows)} merged contribution(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
