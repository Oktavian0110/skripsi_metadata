from github import Github
from config import GITHUB_TOKEN, REPO_LIST, OUTPUT_DIR
from datetime import datetime

def extract_git_metadata():
    results = []
    try:
        g = Github(GITHUB_TOKEN)
        for repo_name in REPO_LIST:
            repo = g.get_repo(repo_name)
            commits = list(repo.get_commits()[:5])  # Ambil 5 commit terbaru
            
            for commit in commits:
                author = commit.author.login if commit.author else "Unknown"
                results.append({
                    "repo": repo_name,
                    "pesan": commit.commit.message[:100],
                    "author": author,
                    "tanggal": commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S")
                })
        return results
    except Exception as e:
        print(f"Error akses GitHub: {e}")
        return []

if __name__ == "__main__":
    git_data = extract_git_metadata()
    print(git_data)