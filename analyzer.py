import pandas as pd
from collections import Counter
import json
import re
from nltk.corpus import stopwords
from radon.visitors import ComplexityVisitor # <-- IMPORT BARU

class Analyzer:
    """
    Menganalisis data dari DataFrame yang sudah diekstrak.
    """

    def analyze_code_complexity(self, files_content):
        """
        FITUR BARU: Menganalisis kompleksitas siklomatis dari file Python.
        """
        complexity_results = []
        if not files_content:
            return complexity_results

        for filepath, content in files_content.items():
            try:
                # Menggunakan Radon untuk menganalisis kode
                visitor = ComplexityVisitor.from_code(content)
                total_complexity = 0
                func_count = 0
                for func in visitor.functions:
                    total_complexity += func.complexity
                    func_count += 1
                
                # Menghitung rata-rata kompleksitas jika ada fungsi
                avg_complexity = total_complexity / func_count if func_count > 0 else 0
                
                if avg_complexity > 0:
                    complexity_results.append({
                        'filepath': filepath,
                        'complexity': round(avg_complexity)
                    })
            except Exception as e:
                print(f"Gagal menganalisis kompleksitas untuk file {filepath}: {e}")
        
        # Mengurutkan hasil dari yang paling kompleks ke yang paling sederhana
        complexity_results.sort(key=lambda x: x['complexity'], reverse=True)
        return complexity_results

    # (Sisa dari file ini tetap sama seperti sebelumnya)
    def analyze_git_data(self, commits_df, deadline=None):
        if commits_df.empty:
            return {}
        
        commits_df['commit_date'] = pd.to_datetime(commits_df['commit_date'])

        total_commits = len(commits_df)
        unique_contributors = commits_df['commit_author'].nunique()
        author_commit_counts = commits_df['commit_author'].value_counts().to_dict()
        category_counts = commits_df['category'].value_counts().to_dict()
        
        commits_over_time = commits_df.set_index('commit_date').resample('D').size().to_dict()
        commits_over_time = {k.strftime('%Y-%m-%d'): v for k, v in commits_over_time.items()}

        stats = {
            'total_commits': total_commits,
            'unique_contributors': unique_contributors,
            'author_commit_counts': author_commit_counts,
            'commit_category_counts': category_counts,
            'commits_over_time': commits_over_time,
            'first_commit_date': commits_df['commit_date'].min().strftime('%Y-%m-%d'),
            'last_commit_date': commits_df['commit_date'].max().strftime('%Y-%m-%d'),
        }

        if deadline:
            deadline_dt = pd.to_datetime(deadline)
            stats['on_time_commits'] = (commits_df['commit_date'] <= deadline_dt).sum()
            stats['late_commits'] = (commits_df['commit_date'] > deadline_dt).sum()

        return stats

    def analyze_team_contribution(self, commits_df):
        if 'files_changed' not in commits_df.columns or commits_df['files_changed'].isnull().all():
            return {}

        author_stats = {}

        for author in commits_df['commit_author'].unique():
            author_stats[author] = {
                'total_commits': 0,
                'lines_added': 0,
                'lines_deleted': 0,
                'files_modified': Counter(),
                'file_types': Counter()
            }

        for _, commit in commits_df.iterrows():
            author = commit['commit_author']
            author_stats[author]['total_commits'] += 1
            
            files_changed = commit['files_changed']
            if not files_changed:
                continue

            if isinstance(files_changed, str):
                try:
                    files_changed = json.loads(files_changed.replace("'", '"'))
                except json.JSONDecodeError:
                    files_changed = []
            
            if not isinstance(files_changed, list):
                continue

            for file in files_changed:
                if not isinstance(file, dict):
                    continue
                author_stats[author]['lines_added'] += file.get('additions', 0)
                author_stats[author]['lines_deleted'] += file.get('deletions', 0)
                
                filename = file.get('filename')
                if filename:
                    file_ext = f".{filename.split('.')[-1]}" if '.' in filename else "No Extension"
                    author_stats[author]['file_types'][file_ext] += 1
        
        for author, stats in author_stats.items():
            stats['file_types'] = dict(stats['file_types'])

        return author_stats

    def analyze_pdf_data(self, pdf_df, deadline=None):
        if pdf_df.empty:
            return {}
        
        stats = {
            'total_documents': len(pdf_df),
            'avg_pages': pdf_df['num_pages'].mean(),
            'avg_word_count': pdf_df['word_count'].mean(),
            'author_counts': pdf_df['author'].value_counts().to_dict(),
        }

        if deadline:
            deadline_dt = pd.to_datetime(deadline).tz_localize('UTC')
            pdf_df['modification_date'] = pd.to_datetime(pdf_df['modification_date'])
            on_time_docs = (pdf_df['modification_date'] <= deadline_dt).sum()
            stats['deadline_status'] = "Tepat Waktu" if on_time_docs > 0 else "Terlambat"

        return stats

    def extract_keywords_from_text(self, text, num_keywords=8):
        if not isinstance(text, str):
            return []
        
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            print("NLTK stopwords for English not found. Downloading...")
            import nltk
            nltk.download('stopwords')
            stop_words = set(stopwords.words('english'))

        stop_words.update(['dan', 'di', 'yang', 'untuk', 'ini', 'itu', 'dengan', 'dalam', 'adalah'])

        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        words = [word for word in words if word not in stop_words and not word.isdigit()]
        
        if not words:
            return []
            
        most_common = Counter(words).most_common(num_keywords)
        return [word for word, count in most_common]
