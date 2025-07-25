import pandas as pd
from collections import Counter
import json
import re # Pastikan re diimpor
from nltk.corpus import stopwords # <-- IMPORT BARU

class Analyzer:
    """
    Menganalisis data dari DataFrame yang sudah diekstrak.
    """

    def analyze_git_data(self, commits_df, deadline=None):
        """Menganalisis data commit dasar."""
        if commits_df.empty:
            return {}
        
        # Pastikan kolom tanggal adalah datetime
        commits_df['commit_date'] = pd.to_datetime(commits_df['commit_date'])

        # Analisis dasar
        total_commits = len(commits_df)
        # PERBAIKAN: Gunakan .get() untuk menghindari error jika kolom tidak ada
        unique_contributors = commits_df['commit_author'].nunique()
        author_commit_counts = commits_df['commit_author'].value_counts().to_dict()
        category_counts = commits_df['category'].value_counts().to_dict()
        
        # Analisis tren waktu
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

        # Analisis deadline jika ada
        if deadline:
            deadline_dt = pd.to_datetime(deadline)
            stats['on_time_commits'] = (commits_df['commit_date'] <= deadline_dt).sum()
            stats['late_commits'] = (commits_df['commit_date'] > deadline_dt).sum()

        return stats

    def analyze_team_contribution(self, commits_df):
        """
        FITUR BARU: Menganalisis kontribusi tim secara mendalam.
        Menghitung baris kode, file yang diubah, dan jenis file per kontributor.
        """
        # PERBAIKAN BUG: Cek jika kolom 'files_changed' ada dan tidak kosong
        if 'files_changed' not in commits_df.columns or commits_df['files_changed'].isnull().all():
            return {}

        author_stats = {}

        # Menginisialisasi statistik untuk setiap author
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
            
            # PERBAIKAN BUG: Handle jika 'files_changed' adalah None atau string kosong
            files_changed = commit['files_changed']
            if not files_changed: # Cek jika None, NaN, atau string kosong
                continue

            if isinstance(files_changed, str):
                try:
                    # Ganti petik tunggal yang tidak valid untuk JSON
                    files_changed = json.loads(files_changed.replace("'", '"'))
                except json.JSONDecodeError:
                    files_changed = [] # Jika string tidak valid, anggap kosong
            
            # Pastikan files_changed adalah list sebelum di-loop
            if not isinstance(files_changed, list):
                continue

            for file in files_changed:
                # Pastikan file adalah dictionary
                if not isinstance(file, dict):
                    continue
                author_stats[author]['lines_added'] += file.get('additions', 0)
                author_stats[author]['lines_deleted'] += file.get('deletions', 0)
                
                filename = file.get('filename')
                if filename:
                    file_ext = f".{filename.split('.')[-1]}" if '.' in filename else "No Extension"
                    author_stats[author]['file_types'][file_ext] += 1
        
        # Mengubah Counter menjadi dict untuk kemudahan di template
        for author, stats in author_stats.items():
            stats['file_types'] = dict(stats['file_types'])

        return author_stats

    def analyze_pdf_data(self, pdf_df, deadline=None):
        """Menganalisis data metadata PDF."""
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
        """
        PERBAIKAN: Mengekstrak kata kunci menggunakan daftar stopwords NLTK yang lebih baik.
        Jumlah kata kunci default diubah menjadi 8.
        """
        if not isinstance(text, str):
            return []
        
        # Mengambil daftar stopwords bahasa Inggris dari NLTK
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            # Fallback jika data stopwords belum di-download (seharusnya sudah di app.py)
            print("NLTK stopwords for English not found. Downloading...")
            import nltk
            nltk.download('stopwords')
            stop_words = set(stopwords.words('english'))

        # Menambahkan beberapa stopwords bahasa Indonesia untuk jaga-jaga
        stop_words.update(['dan', 'di', 'yang', 'untuk', 'ini', 'itu', 'dengan', 'dalam', 'adalah'])

        words = re.findall(r'\b\w{3,}\b', text.lower()) # Ambil kata dengan panjang min 3
        
        # Menyaring kata-kata umum (stopwords)
        words = [word for word in words if word not in stop_words and not word.isdigit()]
        
        if not words:
            return []
            
        # Menghitung 8 kata yang paling sering muncul
        most_common = Counter(words).most_common(num_keywords)
        return [word for word, count in most_common]
