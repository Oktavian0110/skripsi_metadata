# analyzer.py

import pandas as pd
from rake_nltk import Rake
from nltk.corpus import stopwords

class Analyzer:
    """
    A class to analyze metadata from PDF and Git DataFrames.
    """
    def analyze_pdf_data(self, df):
        """
        Analyzes a DataFrame containing PDF metadata.
        """
        if df.empty:
            return {}
        
        first_row = df.iloc[0]
        
        stats = {
            'total_files': len(df),
            'avg_pages': first_row['num_pages'],
            'author_counts': {first_row['author']: 1},
            'keywords': [],
            'analyzed_filename': first_row['file_name']
        }

        if 'full_text' in first_row and pd.notna(first_row['full_text']):
            stats['keywords'] = self.extract_keywords_from_text(first_row['full_text'])
        
        return stats

    def analyze_git_data(self, df):
        """
        Analyzes a DataFrame containing Git commit metadata.
        """
        if df.empty:
            return {
                'total_commits': 0,
                'total_contributors': 0,
                'first_commit_date': 'N/A',
                'last_commit_date': 'N/A',
                'commit_category_counts': {},
                'commits_over_time': {},
                'commit_by_author': {} # Tambahkan key kosong
            }
        
        df['commit_date'] = pd.to_datetime(df['commit_date'])
        
        total_commits = len(df)
        total_contributors = df['commit_author'].nunique()
        first_commit_date = df['commit_date'].min().strftime('%Y-%m-%d %H:%M')
        last_commit_date = df['commit_date'].max().strftime('%Y-%m-%d %H:%M')
        commit_category_counts = df['category'].value_counts().to_dict()
        
        commits_over_time = df.set_index('commit_date').resample('D').size()
        commits_over_time_dict = {
            time.strftime('%Y-%m-%d'): count 
            for time, count in commits_over_time.items()
        }

        # --- LOGIKA BARU: Menghitung commit per author ---
        commit_by_author = df['commit_author'].value_counts().to_dict()

        stats = {
            'total_commits': total_commits,
            'total_contributors': total_contributors,
            'first_commit_date': first_commit_date,
            'last_commit_date': last_commit_date,
            'commit_category_counts': commit_category_counts,
            'commits_over_time': commits_over_time_dict,
            'commit_by_author': commit_by_author # Menambahkan data baru
        }
        return stats
        
    def extract_keywords_from_text(self, text, num_keywords=10):
        """
        Extracts top N keywords/keyphrases from a given text using RAKE.
        """
        if not text or not isinstance(text, str):
            return []
            
        try:
            stop_words_indo = list(stopwords.words('indonesian'))
            rake = Rake(stopwords=stop_words_indo, language='indonesian')
            rake.extract_keywords_from_text(text)
            ranked_phrases = rake.get_ranked_phrases()[:num_keywords]
            return ranked_phrases
        except Exception as e:
            print(f"Error extracting keywords with Rake: {e}")
            return []
