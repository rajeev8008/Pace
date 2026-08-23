import os

os.environ["DATABASE_URL"] = "sqlite://"

from types import SimpleNamespace

from app.api import profiles
from app.api.profiles import username_from_url


def run_checks() -> None:
    assert username_from_url("GITHUB", "https://github.com/rajeev8008") == "rajeev8008"
    assert username_from_url("LEETCODE", "https://leetcode.com/u/rajeev8008/") == "rajeev8008"
    original = profiles.fetch_json
    profiles.fetch_json = lambda _: [{"id": "1", "type": "PushEvent", "created_at": "2026-08-23T12:00:00Z", "repo": {"name": "rajeev/Pace"}, "payload": {"commits": [{}, {}, {}]}}, {"id": "2", "type": "PullRequestEvent", "created_at": "2026-08-23T13:00:00Z", "repo": {"name": "rajeev/Pace"}, "payload": {"action": "opened", "pull_request": {"number": 7, "title": "Improve activity"}}}]
    github_items = profiles.github(SimpleNamespace(username="rajeev"))
    assert github_items[0]["title"] == "3 GitHub commits"
    assert github_items[1]["title"] == "Opened PR #7"
    responses = iter([{"data": {"recentAcSubmissionList": [{"id": "56", "title": "Merge Intervals", "titleSlug": "merge-intervals", "timestamp": "1787486400"}]}}, {"data": {"q0": {"questionFrontendId": "56"}}}])
    profiles.fetch_json = lambda _: next(responses)
    assert profiles.leetcode(SimpleNamespace(username="rajeev"))[0]["title"] == "Solved #56 Merge Intervals"
    profiles.fetch_json = original


if __name__ == "__main__":
    run_checks()
    print("Profile checks passed")
