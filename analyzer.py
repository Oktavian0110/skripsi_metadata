# analyzer.py

import pandas as pd
# from rake_nltk import Rake # <-- Dihapus
import yake # <-- TAMBAHAN: Import library baru
from nltk.corpus import stopwords
from datetime import datetime
import pytz
import re

class Analyzer:
    """
    Menganalisis DataFrame metadata dari PDF dan Git.
    """
    def analyze_pdf_data(self, df, deadline=None):
        """Menganalisis DataFrame metadata PDF."""
        if df.empty:
            return {}
        
        first_row = df.iloc[0]
        
        stats = {
            'total_files': len(df),
            'avg_pages': first_row.get('num_pages', 0),
            'author_counts': {first_row.get('author', 'Unknown'): 1},
            'keywords': [],
            'analyzed_filename': first_row.get('file_name', 'N/A'),
            'deadline_status': None,
            'word_count': first_row.get('word_count', 0),
            'creation_date': pd.to_datetime(first_row.get('creation_date')) if pd.notna(first_row.get('creation_date')) else None
        }

        if 'full_text' in first_row and pd.notna(first_row['full_text']):
            stats['keywords'] = self.extract_keywords_from_text(first_row['full_text'])
        
        if deadline and pd.notna(first_row.get('modification_date')):
            try:
                local_tz = pytz.timezone('Asia/Jakarta')
                deadline_dt = local_tz.localize(datetime.fromisoformat(deadline))
                mod_date_aware = pd.to_datetime(first_row['modification_date'])
                
                if mod_date_aware.astimezone(pytz.utc) <= deadline_dt.astimezone(pytz.utc):
                    stats['deadline_status'] = 'Tepat Waktu'
                else:
                    stats['deadline_status'] = 'Terlambat'
            except (ValueError, TypeError) as e:
                print(f"Error memproses deadline PDF: {e}")

        return stats

    def analyze_git_data(self, df, deadline=None):
        """Menganalisis DataFrame metadata Git."""
        if df.empty:
            return {
                'total_commits': 0, 'total_contributors': 0,
                'first_commit_date': 'N/A', 'last_commit_date': 'N/A',
                'commit_category_counts': {}, 'commits_over_time': {},
                'commit_by_author': {}, 'on_time_commits': 0, 'late_commits': 0,
                'commit_activity_by_day': {}
            }
        
        df['commit_date'] = pd.to_datetime(df['commit_date'])
        
        df['day_of_week'] = df['commit_date'].dt.dayofweek
        day_counts = df['day_of_week'].value_counts().sort_index()
        days_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
        commit_activity = {days_map[day]: count for day, count in day_counts.items()}
        final_activity_data = {day: commit_activity.get(day, 0) for day in days_map.values()}
        
        stats = {
            'total_commits': len(df),
            'total_contributors': df['commit_author'].nunique(),
            'first_commit_date': df['commit_date'].min().strftime('%Y-%m-%d %H:%M'),
            'last_commit_date': df['commit_date'].max().strftime('%Y-%m-%d %H:%M'),
            'commit_category_counts': df['category'].value_counts().to_dict(),
            'commit_by_author': df['commit_author'].value_counts().to_dict(),
            'commits_over_time': {time.strftime('%Y-%m-%d'): count for time, count in df.set_index('commit_date').resample('D').size().items()},
            'commit_activity_by_day': final_activity_data,
            'on_time_commits': 0,
            'late_commits': 0
        }

        if deadline:
            try:
                local_tz = pytz.timezone('Asia/Jakarta')
                deadline_dt_naive = datetime.fromisoformat(deadline)
                deadline_local = local_tz.localize(deadline_dt_naive)
                utc_deadline = deadline_local.astimezone(pytz.utc)
                df['commit_date'] = df['commit_date'].dt.tz_convert(pytz.utc)
                stats['on_time_commits'] = len(df[df['commit_date'] <= utc_deadline])
                stats['late_commits'] = len(df[df['commit_date'] > utc_deadline])
            except (ValueError, TypeError) as e:
                print(f"Error memproses deadline Git: {e}")
        
        return stats
        
    # --- PERBAIKAN TOTAL: Menggunakan library YAKE untuk ekstraksi ---
    def extract_keywords_from_text(self, text, num_keywords=15):
        """Mengekstrak kata kunci dari sebuah teks menggunakan YAKE."""
        if not text or not isinstance(text, str): 
            return []
        
        try:
            # Inisialisasi YAKE untuk bahasa Indonesia ('id')
            # n = ukuran n-gram maksimum, dedupLim = batas untuk deduplikasi, top = jumlah kata kunci
            kw_extractor = yake.KeywordExtractor(lan="id", n=3, dedupLim=0.9, top=num_keywords, features=None)
            
            # YAKE akan melakukan pembersihan teks internal, jadi kita bisa langsung memasukkan teks
            keywords = kw_extractor.extract_keywords(text)
            
            # YAKE mengembalikan list of tuples (keyword, score). Kita hanya butuh keyword-nya.
            return [kw for kw, score in keywords]
            
        except Exception as e:
            print(f"Error saat ekstraksi kata kunci dengan YAKE: {e}")
            return []

