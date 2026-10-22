"Talks to GitHub: reads open issues and adds labels. Nothing else."

import httpx
from pydantic import BaseModel


class Issue(BaseModel):
    number: int
    title: str
    body: str
    labels: frozenset[str]


class GitHub:
    def __init__(self, token: str, repo: str) -> None:
        self.repo = repo
        self.http = httpx.Client(
            base_url="https://api.github.com",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )

    def open_issues(self) -> list[Issue]:
        response = self.http.get(
            f"/repos/{self.repo}/issues", params={"state": "open", "per_page": 100}
        )
        response.raise_for_status()
        return [
            Issue(
                number=item["number"],
                title=item["title"],
                body=item["body"] or "",
                labels=frozenset(label["name"] for label in item["labels"]),
            )
            for item in response.json()
            if "pull_request" not in item  # GitHub's issues list includes pull requests
        ]

    def add_label(self, issue: int, label: str) -> None:
        response = self.http.post(
            f"/repos/{self.repo}/issues/{issue}/labels", json={"labels": [label]}
        )
        response.raise_for_status()
