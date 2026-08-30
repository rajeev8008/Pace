import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_auth
from app.models import Activity, ExternalProfile
from app.schemas import ExternalProfileCreate, ExternalProfileRead


router = APIRouter(prefix="/profiles", tags=["profiles"])


def username_from_url(provider: str, value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc.lower().removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part]
    expected = "github.com" if provider == "GITHUB" else "leetcode.com"
    if host != expected or not parts:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Enter a valid {provider.title()} profile URL")
    if provider == "LEETCODE" and parts[0] == "u":
        parts.pop(0)
    if not parts:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Profile username is missing")
    return parts[0]


def fetch_json(request: Request) -> dict | list:
    try:
        with urlopen(request, timeout=12) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Profile sync failed") from error


def github(profile: ExternalProfile) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Pace"}
    if token := os.getenv("GITHUB_SYNC_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    suffix = "events" if token else "events/public"
    events = fetch_json(Request(f"https://api.github.com/users/{profile.username}/{suffix}?per_page=30", headers=headers))
    items = []
    for event in events:
        payload = event.get("payload", {})
        kind, detail = event.get("type"), event.get("repo", {}).get("name")
        if kind == "PushEvent":
            continue
        elif kind in {"PullRequestEvent", "PullRequestReviewEvent", "PullRequestReviewCommentEvent"}:
            pull = payload.get("pull_request", {})
            action = "Merged" if pull.get("merged") else payload.get("action", "Updated").title()
            title = f"{action} PR #{pull.get('number', '?')}"
            detail = f"{detail} · {pull.get('title', 'Pull request')}"
        elif kind in {"IssuesEvent", "IssueCommentEvent"}:
            issue = payload.get("issue", {})
            action = "Commented on" if kind == "IssueCommentEvent" else payload.get("action", "Updated").title()
            title = f"{action} issue #{issue.get('number', '?')}"
        elif kind == "CreateEvent":
            title = f"Created {payload.get('ref_type', 'repository')} {payload.get('ref') or ''}".strip()
        elif kind == "ReleaseEvent":
            title = f"Published release {payload.get('release', {}).get('tag_name', '')}".strip()
        elif kind == "WatchEvent":
            title = "Starred a repository"
        else:
            title = kind.removesuffix("Event").replace("_", " ") if kind else "GitHub activity"
        items.append({"external_id": f"github:{event['id']}", "title": title, "detail": detail, "occurred_at": datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))})
    commits = fetch_json(Request(f"https://api.github.com/search/commits?q=author%3A{profile.username}&sort=committer-date&order=desc&per_page=100", headers=headers))
    items.extend({"external_id": f"github:commit:{commit['sha']}", "title": "1 GitHub commit", "detail": commit["repository"]["full_name"], "occurred_at": datetime.fromisoformat(commit["commit"]["committer"]["date"].replace("Z", "+00:00"))} for commit in commits.get("items", []))
    return items


def leetcode(profile: ExternalProfile) -> list[dict]:
    query = "query recent($username:String!){recentAcSubmissionList(username:$username,limit:20){id title titleSlug timestamp}}"
    body = json.dumps({"query": query, "variables": {"username": profile.username}}).encode()
    data = fetch_json(Request("https://leetcode.com/graphql", data=body, headers={"Content-Type": "application/json", "User-Agent": "Pace"}))
    submissions = data.get("data", {}).get("recentAcSubmissionList", [])
    slugs = list(dict.fromkeys(item["titleSlug"] for item in submissions))
    numbers = {}
    if slugs:
        variables = {f"slug{i}": slug for i, slug in enumerate(slugs)}
        fields = " ".join(f'q{i}:question(titleSlug:$slug{i}){{questionFrontendId}}' for i in range(len(slugs)))
        declarations = ",".join(f"$slug{i}:String!" for i in range(len(slugs)))
        number_body = json.dumps({"query": f"query numbers({declarations}){{{fields}}}", "variables": variables}).encode()
        number_data = fetch_json(Request("https://leetcode.com/graphql", data=number_body, headers={"Content-Type": "application/json", "User-Agent": "Pace"})).get("data", {})
        numbers = {slug: number_data.get(f"q{i}", {}).get("questionFrontendId") for i, slug in enumerate(slugs)}
    return [{"external_id": f"leetcode:{item['id']}", "title": f"Solved {('#' + numbers[item['titleSlug']] + ' ') if numbers.get(item['titleSlug']) else ''}{item['title']}", "detail": "LeetCode accepted submission", "occurred_at": datetime.fromtimestamp(int(item["timestamp"]), timezone.utc)} for item in submissions]


@router.get("", response_model=list[ExternalProfileRead])
def list_profiles(user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> list[ExternalProfile]:
    return list(db.scalars(select(ExternalProfile).where(ExternalProfile.user_id == user_id).order_by(ExternalProfile.provider)))


@router.post("", response_model=ExternalProfileRead)
def connect(payload: ExternalProfileCreate, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> ExternalProfile:
    username = username_from_url(payload.provider, payload.profile_url)
    profile = db.scalar(select(ExternalProfile).where(ExternalProfile.user_id == user_id, ExternalProfile.provider == payload.provider))
    if profile is None:
        profile = ExternalProfile(user_id=user_id, provider=payload.provider, username=username, profile_url=payload.profile_url)
        db.add(profile)
    else:
        profile.username, profile.profile_url, profile.last_synced_at = username, payload.profile_url, None
    db.commit(); db.refresh(profile)
    return profile


@router.post("/{profile_id}/sync", response_model=ExternalProfileRead)
def sync(profile_id: int, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> ExternalProfile:
    profile = db.scalar(select(ExternalProfile).where(ExternalProfile.id == profile_id, ExternalProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    now = datetime.now(timezone.utc)
    last = profile.last_synced_at
    wait = timedelta(seconds=30) if profile.provider == "LEETCODE" or os.getenv("GITHUB_SYNC_TOKEN") else timedelta(minutes=2)
    if last and (last if last.tzinfo else last.replace(tzinfo=timezone.utc)) > now - wait:
        return profile
    try:
        items = github(profile) if profile.provider == "GITHUB" else leetcode(profile)
    except HTTPException as error:
        if profile.provider == "GITHUB" and not os.getenv("GITHUB_SYNC_TOKEN"):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "GitHub public rate limit reached. Configure GITHUB_SYNC_TOKEN for live sync") from error
        raise
    commits = [item for item in items if item["external_id"].startswith("github:commit:")]
    if commits:
        oldest = min(item["occurred_at"] for item in commits)
        for activity in db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.type == "GITHUB", Activity.title.like("%GitHub commit%"), Activity.occurred_at >= oldest)):
            db.delete(activity)
        db.flush()
    known = {activity.external_id: activity for activity in db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.external_id.in_([item["external_id"] for item in items])))} if items else {}
    for item in items:
        if activity := known.get(item["external_id"]):
            activity.title, activity.detail = item["title"], item["detail"]
        else:
            db.add(Activity(user_id=user_id, type=profile.provider, source_type="profile", source_id=None, **item))
    profile.last_synced_at = now
    db.commit(); db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(profile_id: int, user_id: int = Depends(require_auth), db: Session = Depends(get_db)) -> Response:
    profile = db.scalar(select(ExternalProfile).where(ExternalProfile.id == profile_id, ExternalProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    db.delete(profile); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
