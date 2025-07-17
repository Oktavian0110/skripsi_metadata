import pandas as pd
from github import Github
import re
from datetime import timezone
import os

class GitExtractor:
    """
    Mengekstrak metadata dari repositori GitHub.
    """
    def __init__(self):
        """
        Inisialisasi dengan token.
        """
        # --- OPSI 1 (Tidak Aman, tapi mudah untuk tes): Tempel token Anda di sini ---
        # Ganti None dengan token Anda dalam tanda kutip, contoh: "ghp_xxxxxxxx"
        # PERINGATAN: JANGAN UNGGAH FILE INI KE GITHUB JIKA TOKEN SUDAH DIISI!
        hardcoded_token = "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"
        
        # --- OPSI 2 (Aman, Direkomendasikan): Menggunakan Environment Variable ---
        env_token = os.getenv('GITHUB_API_TOKEN')

        # Program akan menggunakan token yang di-hardcode jika ada,
        # jika tidak, akan mencari dari environment variable.
        final_token = hardcoded_token or env_token
        
        if not final_token:
            raise ValueError("Token GitHub tidak ditemukan. Harap atur sebagai environment variable 'GITHUB_API_TOKEN' atau isi variabel 'hardcoded_token' di git_extractor.py.")
        
        self.github = Github(final_token)

    def _categorize_commit_message(self, message):
        """Memberi kategori pada commit berdasarkan pesannya."""
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
        """Mengekstrak data commit dari sebuah repositori."""
        commits_data = []
        try:
            for commit in repo.get_commits():
                commit_info = {
                    'repo_name': repo.full_name,
                    'commit_sha': commit.sha,
                    'commit_message': commit.commit.message,
                    'commit_author': commit.commit.author.name,
                    'commit_author_email': commit.commit.author.email,
                    'commit_date': commit.commit.author.date.replace(tzinfo=timezone.utc),
                    'category': self._categorize_commit_message(commit.commit.message)
                }
                commits_data.append(commit_info)
        except Exception as e:
            print(f"Error mengekstrak commit: {e}")
        return commits_data

    def _extract_issues(self, repo):
        """Mengekstrak data issue dari sebuah repositori."""
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
                    'issue_created_at': issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at else None,
                    'issue_closed_at': issue.closed_at.replace(tzinfo=timezone.utc) if issue.closed_at else None,
                    'issue_labels': [label.name for label in issue.labels]
                }
                issues_data.append(issue_info)
        except Exception as e:
            print(f"Error mengekstrak issue: {e}")
        return issues_data

    def _extract_pull_requests(self, repo):
        """Mengekstrak data pull request dari sebuah repositori."""
        prs_data = []
        try:
            for pr in repo.get_pulls(state='all'):
                pr_info = {
                    'repo_name': repo.full_name,
                    'pr_number': pr.number,
                    'pr_title': pr.title,
                    'pr_creator': pr.user.login,
                    'pr_state': pr.state,
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
            print(f"Error mengekstrak pull request: {e}")
        return prs_data

    def extract_git_metadata(self, repo_name):
        """Mengekstrak semua metadata dari sebuah repositori."""
        try:
            repo = self.github.get_repo(repo_name)
            commits_list = self._extract_commits(repo)
            issues_list = self._extract_issues(repo)
            prs_list = self._extract_pull_requests(repo)
            return pd.DataFrame(commits_list), pd.DataFrame(issues_list), pd.DataFrame(prs_list)
        except Exception as e:
            print(f"Tidak dapat mengakses repositori {repo_name}. Error: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
