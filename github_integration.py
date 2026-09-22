import os
import hmac
import hashlib
from github import Github
from github.GithubException import GithubException

class GitHubClient:
    def __init__(self, token: str, repo_name: str, dry_run: bool = True):
        self.dry_run = dry_run
        self.repo_name = repo_name
        self.token = token
        if not dry_run:
            self.gh = Github(token)
            self.repo = self.gh.get_repo(repo_name)
        else:
            self.gh = None
            self.repo = None

    def create_hotfix_pr(self, branch_name: str, file_path: str, new_content: str, commit_msg: str, pr_title: str, pr_body: str) -> str:
        if self.dry_run:
            print(f"[GIT DRY-RUN] Creating branch: {branch_name}")
            print(f"[GIT DRY-RUN] Committing file: {file_path}")
            print(f"[GIT DRY-RUN] Opening PR: {pr_title}")
            return "https://github.com/mock/mock/pull/1"

        try:
            # 1. Get default branch
            default_branch = self.repo.default_branch
            sb = self.repo.get_branch(default_branch)

            # 2. Create new branch
            self.repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sb.commit.sha)
            
            # 3. Update file
            contents = self.repo.get_contents(file_path, ref=branch_name)
            self.repo.update_file(contents.path, commit_msg, new_content, contents.sha, branch=branch_name)

            # 4. Create PR
            pr = self.repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base=default_branch)
            print(f"[GIT] PR created successfully: {pr.html_url}")
            return pr.html_url
        except GithubException as e:
            print(f"[GIT ERROR] {e}")
            return ""

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature)
