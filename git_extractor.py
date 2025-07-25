import pandas as pd
from github import Github, Auth, RateLimitExceededException
import re
from datetime import datetime, timezone, timedelta
import os
import time
import json

class GitExtractor:
    """
    Mengekstrak metadata dari repositori GitHub dengan fitur lanjutan:
    - Caching untuk performa
    - Penanganan Rate Limit API
    - Detail perubahan file per commit
    """
    # Memindahkan kategori ke struktur data untuk kemudahan pengelolaan
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
    CACHE_DURATION_SECONDS = 3600 # Cache berlaku selama 1 jam (3600 detik)

    def __init__(self):
        """
        Inisialisasi dengan token dari environment variable.
        """
        # Membuat direktori cache jika belum ada
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        token = os.getenv('GITHUB_API_TOKEN')
        if not token:
            raise ValueError(
                "Token GitHub tidak ditemukan. Harap atur sebagai environment variable 'GITHUB_API_TOKEN'."
            )
        
        auth = Auth.Token(token)
        self.github = Github(auth=auth)

    def _categorize_commit_message(self, message):
        """Memberi kategori pada commit berdasarkan pesannya menggunakan struktur data."""
        if not message:
            return 'Other'
        message_lower = message.lower()
        for category, pattern in self.COMMIT_CATEGORIES.items():
            if re.search(pattern, message_lower):
                return category
        return 'Other'

    def _extract_commits(self, repo):
        """Mengekstrak data commit dari sebuah repositori, termasuk detail file."""
        commits_data = []
        try:
            for commit in repo.get_commits():
                author_name = commit.commit.author.name if commit.commit.author else "Unknown Author"
                author_email = commit.commit.author.email if commit.commit.author else "No Email"
                
                # FITUR BARU: Ekstrak detail file yang berubah
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
                    'files_changed': files_changed # Menambahkan data file
                }
                commits_data.append(commit_info)
        except Exception as e:
            print(f"Error saat mengekstrak commit dari '{repo.full_name}': {e}")
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
            print(f"Error saat mengekstrak issue dari '{repo.full_name}': {e}")
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
            print(f"Error saat mengekstrak pull request dari '{repo.full_name}': {e}")
        return prs_data

    def extract_git_metadata(self, repo_name):
        """
        Mengekstrak semua metadata, dengan implementasi cache dan penanganan rate limit.
        """
        # FITUR BARU: Logika Caching
        cache_filename = os.path.join(self.CACHE_DIR, f"{repo_name.replace('/', '_')}.json")
        if os.path.exists(cache_filename):
            with open(cache_filename, 'r') as f:
                cached_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now(timezone.utc) - cache_time < timedelta(seconds=self.CACHE_DURATION_SECONDS):
                print(f"Menggunakan data dari cache untuk repositori: {repo_name}")
                # Memuat data dari cache ke DataFrame
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

            # FITUR BARU: Simpan hasil ke cache
            new_cache_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'commits': commits_list,
                'issues': issues_list,
                'pull_requests': prs_list,
            }
            with open(cache_filename, 'w') as f:
                json.dump(new_cache_data, f, indent=4, default=str) # default=str untuk handle datetime
            
            return pd.DataFrame(commits_list), pd.DataFrame(issues_list), pd.DataFrame(prs_list)
        
        # FITUR BARU: Penanganan Rate Limit
        except RateLimitExceededException:
            print(f"WARNING: Batas API GitHub tercapai. Mencoba lagi dalam 15 menit.")
            # Di aplikasi nyata, Anda mungkin ingin menunggu (time.sleep) atau memberi tahu pengguna
            # Untuk sekarang, kita kembalikan DataFrame kosong agar aplikasi tidak crash
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        except Exception as e:
            print(f"GAGAL mengakses repositori '{repo_name}'. Penyebab: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
