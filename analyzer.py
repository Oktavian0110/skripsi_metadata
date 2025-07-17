# analyzer.py

import pandas as pd
from rake_nltk import Rake
from nltk.corpus import stopwords
from datetime import datetime
import pytz  # Pastikan library ini sudah terinstal

class Analyzer:
    """
    A class to analyze metadata from PDF and Git DataFrames.
    """
    def analyze_pdf_data(self, df, deadline=None):
        """
        Analyzes a DataFrame containing PDF metadata.
        Optionally compares modification date against a deadline, considering timezones.
        """
        if df.empty:
            return {}
        
        first_row = df.iloc[0]
        
        stats = {
            'total_files': len(df),
            'avg_pages': first_row['num_pages'],
            'author_counts': {first_row['author']: 1},
            'keywords': [],
            'analyzed_filename': first_row['file_name'],
            'deadline_status': None
        }

        if 'full_text' in first_row and pd.notna(first_row['full_text']):
            stats['keywords'] = self.extract_keywords_from_text(first_row['full_text'])
        
        if deadline and pd.notna(first_row['modification_date']):
            try:
                # --- PERBAIKAN LOGIKA TIMEZONE UNTUK PDF (FINAL) ---
                local_tz = pytz.timezone('Asia/Jakarta')

                # 1. Konversi deadline dari form (sudah dalam waktu lokal)
                deadline_dt = local_tz.localize(datetime.fromisoformat(deadline))

                # 2. Ambil tanggal modifikasi PDF (yang naive) dan anggap sebagai waktu lokal
                mod_date_dt = local_tz.localize(pd.to_datetime(first_row['modification_date']))

                # 3. Bandingkan keduanya secara langsung dalam zona waktu yang sama
                if mod_date_dt <= deadline_dt:
                    stats['deadline_status'] = 'Tepat Waktu'
                else:
                    stats['deadline_status'] = 'Terlambat'
            except (ValueError, TypeError) as e:
                print(f"Error processing PDF deadline: {e}")

        return stats

    def analyze_git_data(self, df, deadline=None):
        """
        Analyzes a DataFrame containing Git commit metadata, considering timezones.
        """
        if df.empty:
            return {
                'total_commits': 0, 'total_contributors': 0,
                'first_commit_date': 'N/A', 'last_commit_date': 'N/A',
                'commit_category_counts': {}, 'commits_over_time': {},
                'commit_by_author': {}, 'on_time_commits': 0, 'late_commits': 0
            }
        
        df['commit_date'] = pd.to_datetime(df['commit_date'])
        
        stats = {
            'total_commits': len(df),
            'total_contributors': df['commit_author'].nunique(),
            'first_commit_date': df['commit_date'].min().strftime('%Y-%m-%d %H:%M'),
            'last_commit_date': df['commit_date'].max().strftime('%Y-%m-%d %H:%M'),
            'commit_category_counts': df['category'].value_counts().to_dict(),
            'commit_by_author': df['commit_author'].value_counts().to_dict(),
            'commits_over_time': {time.strftime('%Y-%m-%d'): count for time, count in df.set_index('commit_date').resample('D').size().items()},
            'on_time_commits': 0,
            'late_commits': 0
        }

        if deadline:
            try:
                # Logika untuk Git sudah benar karena Git menggunakan UTC
                local_tz = pytz.timezone('Asia/Jakarta')
                deadline_dt_naive = datetime.fromisoformat(deadline)
                aware_deadline_dt = local_tz.localize(deadline_dt_naive)
                utc_deadline = aware_deadline_dt.astimezone(pytz.utc)

                df['commit_date'] = df['commit_date'].dt.tz_convert(pytz.utc)

                stats['on_time_commits'] = len(df[df['commit_date'] <= utc_deadline])
                stats['late_commits'] = len(df[df['commit_date'] > utc_deadline])
            except (ValueError, TypeError) as e:
                print(f"Error processing Git deadline: {e}")
        
        return stats
        
    def extract_keywords_from_text(self, text, num_keywords=10):
        if not text or not isinstance(text, str): return []
        try:
            rake = Rake(stopwords=list(stopwords.words('indonesian')), language='indonesian')
            rake.extract_keywords_from_text(text)
            return rake.get_ranked_phrases()[:num_keywords]
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
