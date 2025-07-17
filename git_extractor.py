# git_extractor.py

import pandas as pd
from github import Github
from config import GITHUB_TOKEN
import re
from datetime import timezone # Impor timezone

class GitExtractor:
    """
    A class to extract metadata from a GitHub repository, including
    commits, issues, and pull requests.
    """
    def __init__(self, token=GITHUB_TOKEN):
        if not token or token == "MASUKKAN_TOKEN_GITHUB_ANDA_DI_SINI":
            raise ValueError("GitHub token not found or not set. Please set it in config.py")
        self.github = Github(token)

    def _categorize_commit_message(self, message):
        # ... (fungsi ini tidak berubah) ...
        message_lower = message.lower()
        if re.search(r'\b(fix|bug|repair|patch)\b', message_lower): return 'Fix'
        elif re.search(r'\b(feat|feature|add|implement)\b', message_lower): return 'Feature'
        elif re.search(r'\b(docs|document|readme)\b', message_lower): return 'Documentation'
        elif re.search(r'\b(style|format|lint)\b', message_lower): return 'Styling'
        elif re.search(r'\b(refactor|restructure)\b', message_lower): return 'Refactor'
        elif re.search(r'\b(test|testing)\b', message_lower): return 'Test'
        elif re.search(r'\b(chore|build|ci|release)\b', message_lower): return 'Chore'
        else: return 'Other'

    def _extract_commits(self, repo):
        commits_data = []
        try:
            for commit in repo.get_commits():
                commit_info = {
                    'repo_name': repo.full_name,
                    'commit_sha': commit.sha,
                    'commit_message': commit.commit.message,
                    'commit_author': commit.commit.author.name,
                    'commit_author_email': commit.commit.author.email,
                    # PERUBAHAN: Pastikan datetime aware (memiliki info timezone)
                    'commit_date': commit.commit.author.date.replace(tzinfo=timezone.utc),
                    'category': self._categorize_commit_message(commit.commit.message)
                }
                commits_data.append(commit_info)
        except Exception as e:
            print(f"Error extracting commits: {e}")
        return commits_data

    def _extract_issues(self, repo):
        issues_data = []
        try:
            for issue in repo.get_issues(state='all'):
                if issue.pull_request: continue
                issue_info = {
                    'repo_name': repo.full_name,
                    'issue_number': issue.number,
                    'issue_title': issue.title,
                    'issue_creator': issue.user.login,
                    'issue_state': issue.state,
                    # PERUBAHAN: Pastikan datetime aware
                    'issue_created_at': issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at else None,
                    'issue_closed_at': issue.closed_at.replace(tzinfo=timezone.utc) if issue.closed_at else None,
                    'issue_labels': [label.name for label in issue.labels]
                }
                issues_data.append(issue_info)
        except Exception as e:
            print(f"Error extracting issues: {e}")
        return issues_data

    def _extract_pull_requests(self, repo):
        prs_data = []
        try:
            for pr in repo.get_pulls(state='all'):
                pr_info = {
                    'repo_name': repo.full_name,
                    'pr_number': pr.number,
                    'pr_title': pr.title,
                    'pr_creator': pr.user.login,
                    'pr_state': pr.state,
                    # PERUBAHAN: Pastikan datetime aware
                    'pr_created_at': pr.created_at.replace(tzinfo=timezone.utc) if pr.created_at else None,
                    'pr_closed_at': pr.closed_at.replace(tzinfo=timezone.utc) if pr.closed_at else None,
                    'pr_merged': pr.merged,
                    'pr_merged_at': pr.merged_at.replace(tzinfo=timezone.utc) if pr.merged_at else None,
                    'pr_commits': pr.commits,
                    'pr_additions': pr.additions,
                    'pr_deletions': pr.deletions
                }
                prs_data.append(pr_info)
        except Exception as e:
            print(f"Error extracting pull requests: {e}")
        return prs_data

    def extract_git_metadata(self, repo_name):
        try:
            repo = self.github.get_repo(repo_name)
            commits_list = self._extract_commits(repo)
            issues_list = self._extract_issues(repo)
            prs_list = self._extract_pull_requests(repo)
            return pd.DataFrame(commits_list), pd.DataFrame(issues_list), pd.DataFrame(prs_list)
        except Exception as e:
            print(f"Could not access repository {repo_name}. Error: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
