import os

os.environ["DATABASE_URL"] = "sqlite://"

from types import SimpleNamespace

from app.api import profiles
from app.api.profiles import username_from_url


def run_checks() -> None:
    assert username_from_url("GITHUB", "https://github.com/rajeev8008") == "rajeev8008"
    assert username_from_url("LEETCODE", "https://leetcode.com/u/rajeev8008/") == "rajeev8008"
    original, token = profiles.fetch_json, os.environ.get("GITHUB_SYNC_TOKEN")
    requests = []
    os.environ["GITHUB_SYNC_TOKEN"] = "test-token"
    responses = iter([
        [
            {"id": "1", "type": "PushEvent", "created_at": "2026-08-23T12:00:00Z", "repo": {"name": "rajeev/Pace"}, "payload": {}},
            {"id": "2", "type": "PullRequestEvent", "created_at": "2026-08-23T13:00:00Z", "repo": {"name": "rajeev/Pace"}, "payload": {"action": "opened", "pull_request": {"number": 7, "title": "Improve activity"}}},
        ],
        {"items": [{"sha": "abc123", "repository": {"full_name": "rajeev/Pace"}, "commit": {"committer": {"date": "2026-08-23T12:00:00Z"}}}]},
    ])
    profiles.fetch_json = lambda request: requests.append(request) or next(responses)
    github_items = profiles.github(SimpleNamespace(username="rajeev"))
    assert requests[0].full_url.endswith("/users/rajeev/events?per_page=30")
    assert "/search/commits?" in requests[1].full_url
    assert github_items[0]["title"] == "Opened PR #7"
    assert github_items[1]["detail"] == "rajeev/Pace"
    responses = iter([{"data": {"recentAcSubmissionList": [{"id": "56", "title": "Merge Intervals", "titleSlug": "merge-intervals", "timestamp": "1787486400"}]}}, {"data": {"q0": {"questionFrontendId": "56"}}}])
    profiles.fetch_json = lambda _: next(responses)
    assert profiles.leetcode(SimpleNamespace(username="rajeev"))[0]["title"] == "Solved #56 Merge Intervals"
    profiles.fetch_json = original
    if token is None:
        os.environ.pop("GITHUB_SYNC_TOKEN", None)
    else:
        os.environ["GITHUB_SYNC_TOKEN"] = token


if __name__ == "__main__":
    run_checks()
    print("Profile checks passed")
