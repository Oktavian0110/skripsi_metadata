from github import Github
from config import GITHUB_TOKEN, REPO_LIST
from datetime import datetime

def extract_git_metadata(custom_repo_list=None):
    results = []
    
    repos_to_process = custom_repo_list if custom_repo_list is not None else REPO_LIST

    try:
        g = Github(GITHUB_TOKEN)
        for repo_name in repos_to_process:
            repo = g.get_repo(repo_name)
            # Ambil 5 commit terbaru untuk contoh ini
            commits = list(repo.get_commits()[:5]) 
            
            for commit in commits:
                author_name = None
                author_email = None

                # Prioritas 1: Coba ambil dari data login GitHub (paling akurat)
                if commit.author:
                    author_name = commit.author.login
                
                # Prioritas 2: Jika tidak ada, coba dari data committer
                if not author_name and commit.committer:
                    author_name = commit.committer.login

                # Prioritas 3: Jika masih tidak ada, ambil dari data mentah git commit
                if not author_name and commit.commit.author:
                    author_name = commit.commit.author.name
                
                # Ambil email dari data mentah git commit
                if commit.commit.author:
                    author_email = commit.commit.author.email

                # --- Validasi Akhir untuk Membersihkan Data ---
                # Jika nama atau email kosong, atau berisi data aneh, ganti jadi "Unknown"
                if not author_name or not author_name.strip() or author_name.strip() == '=':
                    author_name = "Unknown"
                
                if not author_email or not author_email.strip() or author_email.strip() == '=':
                    author_email = "Unknown"
                
                # Masukkan data yang sudah bersih ke hasil akhir
                results.append({
                    "repo": repo_name,
                    "commit_hash": commit.sha,
                    "pesan": commit.commit.message[:100].replace("\n", " "),
                    "author": author_name,
                    "email": author_email,
                    "tanggal": commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_author_valid": author_name != "Unknown"
                })
        return results
    except Exception as e:
        print(f"Error akses GitHub: {e}")
        return []