import base64
from typing import List, Optional

import httpx

from ..context import ctx
from ..exceptions import ServerErrors

_GITHUB_API = "https://api.github.com"
_GITHUB_REPO = "lncrawl/lightnovel-crawler"
_GITHUB_OWNER = _GITHUB_REPO.split("/")[0]
_DEFAULT_BRANCH = "dev"


class GithubClient:
    def __init__(self) -> None:
        token = ctx.config.app.github_token
        if not token:
            raise ServerErrors.server_error.with_extra("No GitHub Token available")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._gh = httpx.Client(
            headers=headers,
            base_url=_GITHUB_API,
            follow_redirects=True,
        )

    def __enter__(self):
        self._gh.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._gh.__exit__()

    @property
    def internal(self):
        return self._gh

    @staticmethod
    def get_remote_view_link(file_path: str, branch: str = _DEFAULT_BRANCH):
        return f"https://github.com/{_GITHUB_REPO}/blob/{branch}/{file_path.strip('/')}"

    @staticmethod
    def get_remote_edit_link(file_path: str, branch: str = _DEFAULT_BRANCH):
        return f"https://github.com/{_GITHUB_REPO}/edit/{branch}/{file_path.strip('/')}"

    @staticmethod
    def get_remote_raw_link(file_path: str, branch: str = _DEFAULT_BRANCH) -> str:
        return f"https://raw.githubusercontent.com/{_GITHUB_REPO}/{branch}/{file_path.strip('/')}"

    def get_sha(self, branch: str):
        resp = self._gh.get(f"/repos/{_GITHUB_REPO}/git/ref/heads/{branch}")
        resp.raise_for_status()
        data = resp.json()
        return data["object"]["sha"]

    def ensure_branch(self, branch: str) -> None:
        head_sha = self.get_sha(_DEFAULT_BRANCH)
        resp = self._gh.post(
            f"/repos/{_GITHUB_REPO}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": head_sha},
        )
        if resp.status_code == 422:  # branch exists (stale closed PR)
            self._gh.patch(
                f"/repos/{_GITHUB_REPO}/git/refs/heads/{branch}",
                json={"sha": head_sha, "force": True},  # force push
            ).raise_for_status()
        else:
            resp.raise_for_status()

    def get_remote_file(self, file_path: str, branch: str = _DEFAULT_BRANCH):
        params = {"ref": branch} if branch else {}
        resp = self._gh.get(f"/repos/{_GITHUB_REPO}/contents/{file_path}", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data["sha"], data.get("content", "").replace("\n", "")

    def commit_file(
        self,
        *,
        message: str,
        content: str,
        file_path: str,
        branch: str = _DEFAULT_BRANCH,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> bool:
        encoded_content = base64.b64encode(content.encode()).decode()
        file_sha, remote_content = self.get_remote_file(file_path, branch)
        if remote_content == encoded_content:
            return False

        author = {}
        if user_name:
            author["name"] = user_name
        if user_email:
            author["email"] = user_email

        self._gh.put(
            f"/repos/{_GITHUB_REPO}/contents/{file_path}",
            json={
                "sha": file_sha,
                "author": author,
                "branch": branch,
                "message": message,
                "content": encoded_content,
            },
        ).raise_for_status()
        return True

    def find_open_pr(self, branch: str) -> Optional[dict]:
        prs = (
            self._gh.get(
                f"/repos/{_GITHUB_REPO}/pulls",
                params={
                    "head": f"{_GITHUB_OWNER}:{branch}",
                    "base": _DEFAULT_BRANCH,
                    "state": "open",
                    "per_page": 1,
                },
            )
            .raise_for_status()
            .json()
        )
        return prs[0] if prs else None

    def update_pr(self, pr_number: str, title: str, body: str):
        self._gh.patch(
            f"/repos/{_GITHUB_REPO}/pulls/{pr_number}",
            json={"title": title, "body": body},
        ).raise_for_status()

    def create_pr(self, title: str, body: str, branch: str, base: str = _DEFAULT_BRANCH) -> dict:
        resp = self._gh.post(
            f"/repos/{_GITHUB_REPO}/pulls",
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": base,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def add_labels(self, issue_number: str, labels: List[str]) -> list:
        # This endpoint auto-creates labels that do not exist yet.
        resp = self._gh.post(
            f"/repos/{_GITHUB_REPO}/issues/{issue_number}/labels",
            json={"labels": labels},
        )
        resp.raise_for_status()
        return resp.json()

    def search_issues(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 20,
        sort: str = "created",
        order: str = "desc",
    ) -> dict:
        full_query = f"repo:{_GITHUB_REPO} is:issue {query}".strip()
        resp = self._gh.get(
            "/search/issues",
            params={
                "q": full_query,
                "page": page,
                "per_page": per_page,
                "sort": sort,
                "order": order,
                "advanced_search": "true",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def get_issue(self, number: int) -> dict:
        resp = self._gh.get(f"/repos/{_GITHUB_REPO}/issues/{number}")
        resp.raise_for_status()
        return resp.json()

    def create_issue(self, *, title: str, body: str, labels: List[str]) -> dict:
        resp = self._gh.post(
            f"/repos/{_GITHUB_REPO}/issues",
            json={"title": title, "body": body, "labels": labels},
        )
        resp.raise_for_status()
        return resp.json()

    def update_issue(
        self,
        number: int,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> dict:
        payload: dict = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        resp = self._gh.patch(f"/repos/{_GITHUB_REPO}/issues/{number}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete_issue(self, node_id: str) -> None:
        # The REST API cannot delete issues; the GraphQL mutation is the only way.
        mutation = "mutation($id: ID!) { deleteIssue(input: {issueId: $id}) { clientMutationId } }"
        resp = self._gh.post(
            "/graphql",
            json={"query": mutation, "variables": {"id": node_id}},
        )
        resp.raise_for_status()
        errors = resp.json().get("errors")
        if errors:
            raise ServerErrors.server_error.with_extra(str(errors))
