import pandas as pd
from github import Github, Auth, RateLimitExceededException, UnknownObjectException
import re
from datetime import datetime, timezone, timedelta
import os
import time
import json
import base64

class GitExtractor:
    """
    Mengekstrak metadata dari repositori GitHub dengan fitur lanjutan.
    """
    COMMIT_CATEGORIES = {
        'Fix': r'\b(fix|bug|repair|patch)\b',
        'Feature': r'\b(feat|feature|add|implement)\b',
        'Documentation': r'\b(docs|document|readme)\b',
        'Styling': r'\b(style|format|lint)\b',
        'Refactor': r'\b(refactor|restructure)\b',
        'Test': r'\b(test|testing)\b',
        'Chore': r'\b(chore|build|ci|release)\b',
    }
    
    CACHE_DIR = "cache"
    CACHE_DURATION_SECONDS = 3600

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        token = os.getenv('GITHUB_API_TOKEN')
        if not token:
            raise ValueError(
                "Token GitHub tidak ditemukan. Harap atur sebagai environment variable 'GITHUB_API_TOKEN'."
            )
        auth = Auth.Token(token)
        self.github = Github(auth=auth)

    def get_python_files_content(self, repo):
        """
        FITUR BARU: Mengambil konten dari semua file Python (.py) di repositori.
        """
        files_content = {}
        try:
            # Mengambil tree dari branch default
            tree = repo.get_git_tree(repo.default_branch, recursive=True)
            for element in tree.tree:
                if element.path.endswith('.py') and element.type == 'blob':
                    try:
                        # Mengambil konten file
                        content_blob = repo.get_contents(element.path)
                        # Mendekode konten dari base64
                        decoded_content = base64.b64decode(content_blob.content).decode('utf-8')
                        files_content[element.path] = decoded_content
                    except Exception as e:
                        print(f"Gagal mengambil konten file {element.path}: {e}")
        except UnknownObjectException:
            print(f"Branch default '{repo.default_branch}' tidak ditemukan atau repositori kosong.")
        except Exception as e:
            print(f"Error saat mengambil daftar file dari repositori: {e}")
        return files_content

    # (Sisa dari file ini tetap sama seperti sebelumnya)
    def _categorize_commit_message(self, message):
        if not message:
            return 'Other'
        message_lower = message.lower()
        for category, pattern in self.COMMIT_CATEGORIES.items():
            if re.search(pattern, message_lower):
                return category
        return 'Other'

    def _extract_commits(self, repo):
        commits_data = []
        try:
            for commit in repo.get_commits():
                author_name = commit.commit.author.name if commit.commit.author else "Unknown Author"
                author_email = commit.commit.author.email if commit.commit.author else "No Email"
                
                files_changed = []
                for file in commit.files:
                    files_changed.append({
                        'filename': file.filename,
                        'additions': file.additions,
                        'deletions': file.deletions,
                        'changes': file.changes,
                        'status': file.status,
                    })

                commit_info = {
                    'repo_name': repo.full_name,
                    'commit_sha': commit.sha,
                    'commit_message': commit.commit.message,
                    'commit_author': author_name,
                    'commit_author_email': author_email,
                    'commit_date': commit.commit.author.date.replace(tzinfo=timezone.utc),
                    'category': self._categorize_commit_message(commit.commit.message),
                    'files_changed': files_changed
                }
                commits_data.append(commit_info)
        except Exception as e:
            print(f"Error saat mengekstrak commit dari '{repo.full_name}': {e}")
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
                    'issue_created_at': issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at else None,
                    'issue_closed_at': issue.closed_at.replace(tzinfo=timezone.utc) if issue.closed_at else None,
                    'issue_labels': [label.name for label in issue.labels]
                }
                issues_data.append(issue_info)
        except Exception as e:
            print(f"Error saat mengekstrak issue dari '{repo.full_name}': {e}")
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
            print(f"Error saat mengekstrak pull request dari '{repo.full_name}': {e}")
        return prs_data

    def extract_git_metadata(self, repo_name):
        cache_filename = os.path.join(self.CACHE_DIR, f"{repo_name.replace('/', '_')}.json")
        if os.path.exists(cache_filename):
            with open(cache_filename, 'r') as f:
                cached_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now(timezone.utc) - cache_time < timedelta(seconds=self.CACHE_DURATION_SECONDS):
                print(f"Menggunakan data dari cache untuk repositori: {repo_name}")
                commits_df = pd.DataFrame(cached_data.get('commits', []))
                issues_df = pd.DataFrame(cached_data.get('issues', []))
                prs_df = pd.DataFrame(cached_data.get('pull_requests', []))
                return commits_df, issues_df, prs_df

        try:
            print(f"Mencoba mengakses repositori via API: {repo_name}...")
            repo = self.github.get_repo(repo_name)
            print("Repositori berhasil diakses.")
            
            commits_list = self._extract_commits(repo)
            issues_list = self._extract_issues(repo)
            prs_list = self._extract_pull_requests(repo)
            
            print(f"Ekstraksi selesai: {len(commits_list)} commit, {len(issues_list)} issue, {len(prs_list)} PR.")

            new_cache_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'commits': commits_list,
                'issues': issues_list,
                'pull_requests': prs_list,
            }
            with open(cache_filename, 'w') as f:
                json.dump(new_cache_data, f, indent=4, default=str)
            
            return pd.DataFrame(commits_list), pd.DataFrame(issues_list), pd.DataFrame(prs_list)
        
        except RateLimitExceededException:
            print(f"WARNING: Batas API GitHub tercapai. Mencoba lagi dalam 15 menit.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        except Exception as e:
            print(f"GAGAL mengakses repositori '{repo_name}'. Penyebab: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

