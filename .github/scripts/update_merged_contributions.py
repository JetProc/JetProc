#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com"
START_MARKER = "<!-- merged-contributions:start -->"
END_MARKER = "<!-- merged-contributions:end -->"
GROUPS = (
    ("code", "Code Contributions"),
    ("docs", "Documentation / Community"),
)

# Reviewed classifications are explicit: a repository can contain both code and docs PRs.
# Open PRs in this catalog are NOT published until the API confirms merged_at.
# Add a category here after reviewing a newly discovered contribution; unknown PRs
# are reported, not silently classified or mixed with team/educational projects.
CONTRIBUTIONS = {
    "https://github.com/toss/react-simplikit/pull/473": (
        "code", "useLongPress의 unmount 이후 콜백 실행 방지 및 회귀 테스트 추가"
    ),
    "https://github.com/toss/es-toolkit/pull/1726": (
        "code", "isNumber 판별 기준을 다른 타입 가드와 일치하도록 수정"
    ),
    "https://github.com/akan-team/akanjs/pull/15": (
        "code", "무한 스크롤 중복 요청 수정"
    ),
    "https://github.com/akan-team/akanjs/pull/16": (
        "code", "파일 미리보기 URL 경로 오류 수정"
    ),
    "https://github.com/reactjs/ko.react.dev/pull/1525": (
        "docs", "테스트 도구 지원 중단 안내 한국어 번역"
    ),
    "https://github.com/lodash/lodash/pull/6196": (
        "docs", "기여 가이드 링크 오류 수정"
    ),
    "https://github.com/lodash/lodash/pull/6213": (
        "code", "배열로 감싼 prototype 경로의 omit·unset 회귀 테스트 추가"
    ),
    "https://github.com/toss/overlay-kit/pull/229": (
        "docs", "컨텍스트 접근을 위한 OverlayProvider 배치 안내 보완"
    ),
    "https://github.com/TanStack/query/pull/10885": (
        "code", "Svelte createQuery의 query별 persister 타입 추론 보완"
    ),
}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    try:
        value = int(raw) if raw else default
        return value if value > 0 else default
    except ValueError:
        return default


def split_csv(value: str | None) -> set[str]:
    return {part.strip().lower() for part in (value or "").split(",") if part.strip()}


def request_json(url: str, token: str | None = None) -> dict[str, Any]:
    # Never forward a token to a URL supplied by an unexpected API response.
    if not url.startswith(f"{API_ROOT}/"):
        raise RuntimeError("Refusing a non-GitHub API URL.")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "JetProc-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"GitHub API request failed: HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"GitHub API request failed: {error.reason}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected GitHub API response shape.")
    return payload


def search_merged_pull_requests(
    username: str,
    excluded_owners: set[str],
    fetch_limit: int,
    token: str | None,
    excluded_repos: set[str] | None = None,
) -> list[dict[str, Any]]:
    exclusions = " ".join(f"-user:{owner}" for owner in sorted(excluded_owners))
    repo_exclusions = " ".join(f"-repo:{repo}" for repo in sorted(excluded_repos or set()))
    query = f"is:pr is:merged author:{username} archived:false {exclusions} {repo_exclusions}".strip()
    params = urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": min(fetch_limit, 100)})
    payload = request_json(f"{API_ROOT}/search/issues?{params}", token)
    items = payload.get("items")
    if payload.get("incomplete_results") or not isinstance(items, list):
        raise RuntimeError("Incomplete contribution search; preserving README.")
    # Do not silently drop older reviewed rows when the one-page search becomes full.
    if payload.get("total_count", len(items)) > len(items):
        raise RuntimeError("Contribution search needs pagination; preserving README.")
    return items


def load_pull_request_details(item: dict[str, Any], token: str | None) -> dict[str, Any] | None:
    api_url = (item.get("pull_request") or {}).get("url")
    return request_json(api_url, token) if api_url else None


def normalize_pull_requests(
    items: list[dict[str, Any]],
    username: str,
    excluded_owners: set[str],
    max_items: int,
    token: str | None,
    excluded_repos: set[str] | None = None,
) -> list[dict[str, str]]:
    seen_urls: set[str] = set()
    rows: list[dict[str, str]] = []
    for item in items:
        details = load_pull_request_details(item, token)
        if not details or not details.get("merged_at"):
            continue
        if (details.get("user") or {}).get("login", "").lower() != username.lower():
            continue
        repo = ((details.get("base") or {}).get("repo") or {})
        full_name = repo.get("full_name")
        repo_url = repo.get("html_url")
        if not full_name or not repo_url:
            continue
        owner = full_name.split("/", 1)[0].lower()
        if owner == username.lower() or owner in excluded_owners:
            continue
        if full_name.lower() in (excluded_repos or set()) or repo.get("private") or repo.get("archived"):
            continue
        url = details.get("html_url")
        if not url or url in seen_urls:
            continue
        reviewed = CONTRIBUTIONS.get(url)
        if not reviewed:
            print(f"Unclassified contribution, review before publishing: {url}", file=sys.stderr)
            continue
        category, summary = reviewed
        seen_urls.add(url)
        rows.append({
            "merged_at": details["merged_at"], "repo": full_name, "repo_url": repo_url,
            "number": str(details.get("number") or item.get("number") or ""),
            "title": details.get("title") or item.get("title") or "Merged pull request",
            "url": url, "category": category, "summary": summary,
        })
    rows.sort(key=lambda row: (row["merged_at"], row["url"]), reverse=True)
    return rows[:max_items]


def escape_markdown(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("|", "\\|")
            .replace("[", "\\[").replace("]", "\\]")
            .replace("\r", " ").replace("\n", " ").strip())


def render_rows(rows: list[dict[str, str]]) -> str:
    sections = []
    for category, title in GROUPS:
        lines = [f"### {title}", ""]
        group = [row for row in rows if row["category"] == category]
        if not group:
            lines.append("_병합이 확인된 기여가 없습니다._")
        else:
            lines.extend(["| 저장소 | 기여 내용 | PR |", "|:---|:---|:---|"])
            for row in group:
                lines.append(
                    f"| [{escape_markdown(row['repo'])}]({row['repo_url']}) | "
                    f"{escape_markdown(row['summary'])} | "
                    f"[#{escape_markdown(row['number'])}]({row['url']}) |"
                )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def replace_marker_block(readme: str, rendered: str) -> str:
    if readme.count(START_MARKER) != 1 or readme.count(END_MARKER) != 1:
        raise RuntimeError("README must contain exactly one contribution marker pair.")
    start = readme.index(START_MARKER)
    end = readme.index(END_MARKER)
    if start >= end:
        raise RuntimeError("Contribution markers are out of order.")
    # Slicing preserves all surrounding content and treats backslashes literally.
    return readme[:start] + f"{START_MARKER}\n{rendered}\n{END_MARKER}" + readme[end + len(END_MARKER):]


def main() -> int:
    username = os.environ.get("GITHUB_USERNAME")
    if not username:
        raise RuntimeError("GITHUB_USERNAME is required.")
    path = Path(os.environ.get("README_PATH", "README.md"))
    readme = path.read_text(encoding="utf-8")
    replace_marker_block(readme, "")  # Validate boundaries before requesting data.
    max_items = env_int("MAX_ITEMS", 12)
    excluded_owners = split_csv(os.environ.get("EXCLUDED_OWNERS")) | {username.lower()}
    excluded_repos = split_csv(os.environ.get("EXCLUDED_REPOS"))
    token = os.environ.get("CONTRIBUTIONS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    items = search_merged_pull_requests(
        username, excluded_owners, env_int("FETCH_LIMIT", max(max_items * 4, 40)), token, excluded_repos
    )
    rows = normalize_pull_requests(items, username, excluded_owners, max_items, token, excluded_repos)
    if not rows:
        raise RuntimeError("No verified categorized contributions; preserving README.")
    updated = replace_marker_block(readme, render_rows(rows))
    if updated != readme:
        path.write_text(updated, encoding="utf-8")
    print(f"Verified {len(rows)} merged contribution(s) in {path}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
