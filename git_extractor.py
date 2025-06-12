from github import Github
from config import GITHUB_TOKEN, REPO_LIST
from datetime import datetime
from analyzer import kategorikan_commit # <-- 1. IMPORT FUNGSI BARU

def extract_git_metadata(custom_repo_list=None):
    results = []
    
    repos_to_process = custom_repo_list if custom_repo_list is not None else REPO_LIST

    try:
        g = Github(GITHUB_TOKEN)
        for repo_name in repos_to_process:
            repo = g.get_repo(repo_name)
            commits = list(repo.get_commits()[:5]) 
            
            for commit in commits:
                author_name = None
                author_email = None

                if commit.author: author_name = commit.author.login
                if not author_name and commit.committer: author_name = commit.committer.login
                if not author_name and commit.commit.author: author_name = commit.commit.author.name
                if commit.commit.author: author_email = commit.commit.author.email

                if not author_name or not author_name.strip() or author_name.strip() == '=': author_name = "Unknown"
                if not author_email or not author_email.strip() or author_email.strip() == '=': author_email = "Unknown"

                # --- PERUBAHAN UTAMA DI SINI ---
                # 2. Panggil fungsi analisis untuk mendapatkan kategori
                pesan_commit = commit.commit.message
                kategori = kategorikan_commit(pesan_commit)
                
                results.append({
                    "repo": repo_name,
                    "commit_hash": commit.sha,
                    "pesan": pesan_commit[:100].replace("\n", " "),
                    "author": author_name,
                    "email": author_email,
                    "tanggal": commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_author_valid": author_name != "Unknown",
                    "kategori": kategori # <-- 3. Tambahkan kategori ke hasil
                })
        return results
    except Exception as e:
        print(f"Error akses GitHub: {e}")
        return []