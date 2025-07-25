# app.py

import os
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
import pandas as pd
import math
from werkzeug.utils import secure_filename
import nltk
import re
import json
from datetime import datetime # Import datetime
import pytz # Import library pytz untuk zona waktu

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pdf_extractor import PdfExtractor
from git_extractor import GitExtractor
from analyzer import Analyzer

# --- Inisialisasi Awal Aplikasi ---
# (Tidak ada perubahan di bagian ini)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK stopwords data...")
    nltk.download('stopwords')
    print("Download complete.")

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK punkt data...")
    nltk.download('punkt')
    print("Download complete.")

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'skripsi_metadata_db'
}

app = Flask(__name__)
app.secret_key = 'supersecretkey_yang_lebih_aman'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- FUNGSI BARU UNTUK KONVERSI ZONA WAKTU ---
def to_local_time(utc_dt):
    """Mengonversi datetime UTC ke zona waktu lokal (Asia/Jakarta)."""
    if not isinstance(utc_dt, datetime):
        return utc_dt # Kembalikan nilai asli jika bukan datetime
    try:
        local_tz = pytz.timezone('Asia/Jakarta')
        local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
        return local_dt
    except Exception:
        return utc_dt # Fallback jika terjadi error

# Daftarkan fungsi sebagai filter Jinja2
app.jinja_env.filters['localtime'] = to_local_time


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

pdf_extractor = PdfExtractor()
git_extractor = GitExtractor()
analyzer = Analyzer()


# --- Fungsi-fungsi Database ---
# (Tidak ada perubahan di semua fungsi database)
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        flash(f"Error koneksi database: {err}", "danger")
        return None

def save_pdf_to_db(df):
    conn = get_db_connection()
    if not conn: return None, None
    last_id = None
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO pdf_documents (file_name, title, author, num_pages, creation_date, modification_date, keywords, word_count, full_text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        for _, row in df.iterrows():
            keywords_list = row.get('keywords', [])
            keywords_str = ", ".join(keywords_list) if isinstance(keywords_list, list) else ""
            mod_date = row['modification_date'] if pd.notna(row['modification_date']) else None
            create_date = row['creation_date'] if pd.notna(row['creation_date']) else None
            word_count = int(row['word_count']) if pd.notna(row['word_count']) else 0
            full_text = row.get('full_text', '')
            
            cursor.execute(sql, (row['file_name'], row['title'], row['author'], int(row['num_pages']), create_date, mod_date, keywords_str, word_count, full_text))
            last_id = cursor.lastrowid
        conn.commit()
        return True, last_id
    except Exception as e:
        print(f"Error saving PDF data: {e}")
        return False, None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def save_git_data_to_db(commits_df, issues_df, prs_df):
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        if not commits_df.empty:
            sql_commits = "INSERT INTO git_commits (repo_name, commit_sha, commit_message, commit_author, commit_author_email, commit_date, category, files_changed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            for _, row in commits_df.iterrows():
                files_changed_json = json.dumps(row.get('files_changed', []))
                cursor.execute(sql_commits, (row['repo_name'], row['commit_sha'], row['commit_message'], row['commit_author'], row['commit_author_email'], row['commit_date'], row['category'], files_changed_json))
        
        if not issues_df.empty:
            sql_issues = "INSERT INTO git_issues (repo_name, issue_number, issue_title, issue_creator, issue_state, issue_created_at, issue_closed_at, issue_labels) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            for _, row in issues_df.iterrows():
                labels_str = ", ".join(row.get('issue_labels', []))
                cursor.execute(sql_issues, (row['repo_name'], int(row['issue_number']), row['issue_title'], row['issue_creator'], row['issue_state'], row['issue_created_at'], row['issue_closed_at'], labels_str))
        if not prs_df.empty:
            sql_prs = "INSERT INTO git_pull_requests (repo_name, pr_number, pr_title, pr_creator, pr_state, pr_created_at, pr_closed_at, pr_merged, pr_merged_at, pr_commits, pr_additions, pr_deletions) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            for _, row in prs_df.iterrows():
                cursor.execute(sql_prs, (row['repo_name'], int(row['pr_number']), row['pr_title'], row['pr_creator'], row['pr_state'], row['pr_created_at'], row['pr_closed_at'], bool(row['pr_merged']), row['pr_merged_at'], int(row['pr_commits']), int(row['pr_additions']), int(row['pr_deletions'])))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving Git data: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- Fungsi-fungsi Helper ---
# (Tidak ada perubahan di sini)
def check_similarity(new_doc_id, new_doc_text):
    conn = get_db_connection()
    if not conn: return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, file_name, full_text FROM pdf_documents WHERE id != %s", (new_doc_id,))
        existing_docs = [doc for doc in cursor.fetchall() if doc.get('full_text')]

        if not existing_docs or not new_doc_text:
            return

        corpus = [new_doc_text] + [doc['full_text'] for doc in existing_docs]
        
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(corpus)
        similarity_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix)
        
        similarity_scores = similarity_matrix[0][1:]
        for i, score in enumerate(similarity_scores):
            if score > 0.90:
                existing_doc_id = existing_docs[i]['id']
                cursor.execute(
                    "INSERT INTO pdf_similarity (doc1_id, doc2_id, similarity_score) VALUES (%s, %s, %s)",
                    (new_doc_id, existing_doc_id, float(score))
                )
        conn.commit()

    except Exception as e:
        print(f"Error saat memeriksa kemiripan: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def analyze_and_save_pdfs(pdf_metadata_list, deadline=None):
    if not pdf_metadata_list:
        return False
    
    local_analyzer = Analyzer()
    df = pd.DataFrame(pdf_metadata_list)
    df['keywords'] = df['full_text'].apply(lambda text: local_analyzer.extract_keywords_from_text(text))
    
    is_saved, last_id = save_pdf_to_db(df)
    
    if is_saved and last_id:
        new_doc_text = df.iloc[0]['full_text']
        check_similarity(last_id, new_doc_text)
        if deadline:
            stats = local_analyzer.analyze_pdf_data(df.iloc[[0]], deadline)
            if stats.get('deadline_status'):
                flash(f"Status Pengumpulan: {stats['deadline_status']}", "info")
        return True
    else:
        return False

# --- Rute-rute Aplikasi Flask ---
# (Semua rute tetap sama, tidak perlu diubah)

@app.route('/')
def dashboard():
    pdf_stats, git_stats = {}, {}
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM pdf_documents ORDER BY analysis_timestamp DESC LIMIT 1")
            latest_pdf = cursor.fetchone()
            if latest_pdf:
                pdf_stats = { 'analyzed_filename': latest_pdf.get('file_name'), 'author_counts': {latest_pdf.get('author'): 1}, 'avg_pages': latest_pdf.get('num_pages'), 'word_count': latest_pdf.get('word_count'), 'creation_date': latest_pdf.get('creation_date'), 'keywords': latest_pdf.get('keywords', '').split(',') if latest_pdf.get('keywords') else [] }
            cursor.execute("SELECT repo_name FROM git_commits ORDER BY analysis_timestamp DESC LIMIT 1")
            latest_git_repo = cursor.fetchone()
            if latest_git_repo:
                repo_name = latest_git_repo['repo_name']
                cursor.execute("SELECT commit_date, category, commit_author FROM git_commits WHERE repo_name = %s", (repo_name,))
                commits_data = cursor.fetchall()
                if commits_data:
                    commits_df_from_db = pd.DataFrame(commits_data)
                    git_stats = analyzer.analyze_git_data(commits_df_from_db)
                    cursor.execute("SELECT COUNT(*) as count FROM git_issues WHERE repo_name = %s", (repo_name,))
                    git_stats['total_issues'] = cursor.fetchone().get('count', 0)
                    cursor.execute("SELECT COUNT(*) as count FROM git_pull_requests WHERE repo_name = %s", (repo_name,))
                    git_stats['total_pull_requests'] = cursor.fetchone().get('count', 0)
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    commits_over_time_data = git_stats.get('commits_over_time', {})
    commit_category_chart_data = git_stats.get('commit_category_counts', {})
    
    return render_template('dashboard.html', pdf_stats=pdf_stats, git_stats=git_stats, commits_over_time_data=commits_over_time_data, commit_category_chart_data=commit_category_chart_data)

@app.route('/data-master')
def data_master():
    search_query = request.args.get('q', '').strip()
    context = { 'headers': [], 'data': [], 'total_pages': 1, 'current_page': request.args.get('page', 1, type=int), 'active_tab': request.args.get('tab', 'pdf'), 'search_query': search_query }
    conn = get_db_connection()
    if not conn:
        flash("Koneksi ke database gagal.", "danger")
        return render_template('data_master.html', **context)
    
    try:
        per_page = 10
        offset = (context['current_page'] - 1) * per_page
        cursor = conn.cursor(dictionary=True)
        
        params = []
        where_clauses = []

        if context['active_tab'] == 'pdf':
            context['headers'] = ["ID", "Nama File", "Judul", "Author", "Jml Halaman", "Waktu Analisis", "Aksi"]
            base_query = "FROM pdf_documents"
            if search_query:
                like_query = f"%{search_query}%"
                where_clauses.append("(file_name LIKE %s OR title LIKE %s OR author LIKE %s)")
                params.extend([like_query, like_query, like_query])
            
            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            count_query = f"SELECT COUNT(*) as count {base_query}{where_sql}"
            data_query = f"SELECT id, file_name, title, author, num_pages, analysis_timestamp {base_query}{where_sql} ORDER BY analysis_timestamp DESC LIMIT %s OFFSET %s"
            params.extend([per_page, offset])

        elif context['active_tab'] == 'git':
            context['headers'] = ["Nama Repositori", "Total Commit", "Kontributor", "Commit Terakhir", "Aksi"]
            base_query = "FROM git_commits"
            group_by_sql = " GROUP BY repo_name"
            having_sql = ""
            if search_query:
                like_query = f"%{search_query}%"
                having_sql = " HAVING repo_name LIKE %s"
                params.append(like_query)
            
            count_query = f"SELECT COUNT(*) as count FROM (SELECT repo_name {base_query}{group_by_sql}{having_sql}) as subquery"
            data_query = f"SELECT repo_name, COUNT(commit_sha) as total_commits, COUNT(DISTINCT commit_author) as contributors, MAX(commit_date) as last_commit {base_query}{group_by_sql}{having_sql} ORDER BY last_commit DESC LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
        else:
            return redirect(url_for('data_master', tab='pdf'))
        
        cursor.execute(count_query, params[:-2] if search_query else [])
        total_rows = cursor.fetchone()['count']
        context['total_pages'] = int(math.ceil(total_rows / per_page)) if total_rows > 0 else 1
        
        cursor.execute(data_query, params)
        context['data'] = cursor.fetchall()

    except Exception as e:
        print(f"Error in data_master: {e}")
        flash("Terjadi kesalahan saat memuat data master.", "danger")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('data_master.html', **context)

@app.route('/visualisasi')
def visualisasi():
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT commit_author, COUNT(*) as total_commits FROM git_commits GROUP BY commit_author ORDER BY total_commits DESC LIMIT 10")
        git_contributors = cursor.fetchall()
        
        cursor.execute("SELECT category, COUNT(*) as total_commits FROM git_commits GROUP BY category")
        git_categories = cursor.fetchall()

        cursor.execute("SELECT author, COUNT(*) as total_docs FROM pdf_documents GROUP BY author ORDER BY total_docs DESC LIMIT 10")
        pdf_authors = cursor.fetchall()
        
        git_contributors_data = {item['commit_author']: item['total_commits'] for item in git_contributors}
        git_categories_data = {item['category']: item['total_commits'] for item in git_categories}
        pdf_authors_data = {item['author']: item['total_docs'] for item in pdf_authors}

    except Exception as e:
        flash(f"Error saat mengambil data visualisasi: {e}", "danger")
        return redirect(url_for('dashboard'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('visualisasi.html', 
                           git_contributors_data=git_contributors_data,
                           git_categories_data=git_categories_data,
                           pdf_authors_data=pdf_authors_data)

@app.route('/repo/<path:repo_name>')
def repo_detail(repo_name):
    conn = get_db_connection()
    if not conn: return redirect(url_for('data_master', tab='git'))
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM git_commits WHERE repo_name = %s", (repo_name,))
        commits = cursor.fetchall()
        if not commits:
            flash(f"Tidak ditemukan data untuk repositori {repo_name}", "warning")
            return redirect(url_for('data_master', tab='git'))
        
        df_commits = pd.DataFrame(commits)
        
        git_stats = analyzer.analyze_git_data(df_commits)
        team_contribution = analyzer.analyze_team_contribution(df_commits)

        cursor.execute("SELECT COUNT(*) as count FROM git_issues WHERE repo_name = %s", (repo_name,))
        git_stats['total_issues'] = cursor.fetchone().get('count', 0)
        cursor.execute("SELECT COUNT(*) as count FROM git_pull_requests WHERE repo_name = %s", (repo_name,))
        git_stats['total_pull_requests'] = cursor.fetchone().get('count', 0)

    except Exception as e:
        flash(f"Error saat mengambil detail repo: {e}", "danger")
        return redirect(url_for('data_master', tab='git'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('repo_detail.html', repo_name=repo_name, stats=git_stats, commits=commits, team_contribution=team_contribution)

@app.route('/profile/<author_name>')
def student_profile(author_name):
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, file_name, title, author, num_pages, analysis_timestamp FROM pdf_documents WHERE author = %s ORDER BY analysis_timestamp DESC", (author_name,))
        pdf_docs = cursor.fetchall()

        cursor.execute("""
            SELECT repo_name, COUNT(commit_sha) as total_commits, MAX(commit_date) as last_commit
            FROM git_commits 
            WHERE commit_author = %s 
            GROUP BY repo_name 
            ORDER BY last_commit DESC
        """, (author_name,))
        git_repos = cursor.fetchall()

        total_pdf = len(pdf_docs)
        total_git_commits = sum(repo['total_commits'] for repo in git_repos)

        profile_data = {
            'author_name': author_name,
            'pdf_documents': pdf_docs,
            'git_repositories': git_repos,
            'total_pdf_submissions': total_pdf,
            'total_git_commits': total_git_commits
        }

    except Exception as e:
        flash(f"Error saat memuat profil untuk {author_name}: {e}", "danger")
        return redirect(url_for('dashboard'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('student_profile.html', profile=profile_data)

@app.route('/pdf/<int:doc_id>')
def pdf_detail(doc_id):
    conn = get_db_connection()
    if not conn: return redirect(url_for('data_master', tab='pdf'))
    
    doc = None
    similar_docs = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pdf_documents WHERE id = %s", (doc_id,))
        doc = cursor.fetchone()
        if not doc:
            flash(f"Tidak ditemukan dokumen dengan ID {doc_id}", "warning")
            return redirect(url_for('data_master', tab='pdf'))
        
        if doc.get('keywords'):
            doc['keywords_list'] = [k.strip() for k in doc['keywords'].split(',') if k.strip()]
        else:
            doc['keywords_list'] = []

        query_similarity = """
            (SELECT s.similarity_score, d.id, d.file_name 
             FROM pdf_similarity s
             JOIN pdf_documents d ON s.doc2_id = d.id
             WHERE s.doc1_id = %s)
            UNION
            (SELECT s.similarity_score, d.id, d.file_name
             FROM pdf_similarity s
             JOIN pdf_documents d ON s.doc1_id = d.id
             WHERE s.doc2_id = %s)
            ORDER BY similarity_score DESC
        """
        cursor.execute(query_similarity, (doc_id, doc_id))
        similar_docs = cursor.fetchall()

    except Exception as e:
        flash(f"Error saat mengambil detail dokumen: {e}", "danger")
        return redirect(url_for('data_master', tab='pdf'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('pdf_detail.html', doc=doc, similar_docs=similar_docs)


@app.route('/analyze-pdf', methods=['POST'])
def analyze_pdf():
    link = request.form.get('gdrive_link')
    deadline = request.form.get('deadline')
    if not link:
        flash('Link Google Drive tidak boleh kosong.', 'warning')
        return redirect(url_for('dashboard'))
    status, pdf_metadata_list = pdf_extractor.extract_metadata_from_gdrive_links([link])
    if status == 'success':
        is_success = analyze_and_save_pdfs(pdf_metadata_list, deadline)
        if is_success:
            flash('Dokumen berhasil dianalisis dan disimpan.', 'success')
    elif status == 'private':
        flash("Gagal: File bersifat privat. Ubah setelan berbagi.", "danger")
    else:
        flash("Gagal mengekstrak metadata dari link.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/upload-and-analyze-pdf', methods=['POST'])
def upload_and_analyze_pdf():
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih.', 'warning')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('Tidak ada file yang dipilih.', 'warning')
        return redirect(url_for('dashboard'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'pdf':
                status, metadata_list = pdf_extractor.extract_metadata_from_local_file(filepath)
                if status == 'success':
                    is_success = analyze_and_save_pdfs(metadata_list)
                    if is_success:
                        flash(f'Dokumen PDF "{filename}" berhasil dianalisis dan disimpan.', 'success')
                else:
                    flash(f'Gagal memproses file PDF "{filename}".', 'danger')
            elif file_extension in ['xlsx', 'csv']:
                if file_extension == 'csv': df_links = pd.read_csv(filepath)
                else: df_links = pd.read_excel(filepath)
                if 'link' not in df_links.columns:
                    flash("File harus memiliki kolom bernama 'link'.", "danger")
                    return redirect(url_for('dashboard'))
                links = df_links['link'].tolist()
                all_metadata = []
                success_count, fail_count = 0, 0
                for link in links:
                    status, metadata_list = pdf_extractor.extract_metadata_from_gdrive_links([link])
                    if status == 'success':
                        all_metadata.extend(metadata_list)
                        success_count += 1
                    else:
                        fail_count += 1
                if all_metadata:
                    is_success = analyze_and_save_pdfs(all_metadata)
                    if is_success:
                        flash(f'Analisis massal selesai: {success_count} berhasil, {fail_count} gagal. Data berhasil disimpan.', 'success')
                else:
                    flash('Analisis massal selesai, namun tidak ada data yang berhasil diekstrak.', 'warning')
        except Exception as e:
            flash(f"Terjadi kesalahan saat memproses file: {e}", "danger")
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
        return redirect(url_for('dashboard'))
    else:
        flash('Format file tidak didukung. Harap unggah file .pdf, .xlsx, atau .csv.', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/analyze-git', methods=['POST'])
def analyze_git():
    repo_input = request.form.get('repo_name', '').strip()
    deadline = request.form.get('deadline')

    if not repo_input:
        flash('Nama repositori tidak boleh kosong.', 'warning')
        return redirect(url_for('dashboard'))

    match = re.search(r'github\.com/([\w-]+/[\w.-]+)', repo_input)
    if match:
        repo_name = match.group(1)
    else:
        repo_name = repo_input

    try:
        commits_df, issues_df, prs_df = git_extractor.extract_git_metadata(repo_name)
        if commits_df.empty and issues_df.empty and prs_df.empty:
            flash(f'Gagal mengambil data atau repositori "{repo_name}" kosong.', 'danger')
        else:
            if save_git_data_to_db(commits_df, issues_df, prs_df):
                flash(f'Data untuk repositori "{repo_name}" berhasil disimpan.', 'success')
            if deadline and not commits_df.empty:
                deadline_stats = analyzer.analyze_git_data(commits_df, deadline)
                flash(f"Hasil Analisis Deadline: Tepat Waktu: {deadline_stats['on_time_commits']} commit, Terlambat: {deadline_stats['late_commits']} commit.", "info")
    except Exception as e:
        flash(f"Terjadi error saat analisis Git: {e}", "danger")

    return redirect(url_for('dashboard'))
    
@app.route('/clear-cache/<path:repo_name>', methods=['POST'])
def clear_cache(repo_name):
    try:
        cache_dir = "cache"
        sanitized_repo_name = repo_name.replace('/', '_')
        cache_file = os.path.join(cache_dir, f"{sanitized_repo_name}.json")
        
        if os.path.exists(cache_file):
            os.remove(cache_file)
            flash(f"Cache untuk repositori {repo_name} berhasil dihapus. Data akan diambil ulang dari API.", "info")
        else:
            flash(f"Tidak ada cache yang ditemukan untuk repositori {repo_name}.", "warning")
    except Exception as e:
        flash(f"Gagal menghapus cache: {e}", "danger")
        
    return redirect(url_for('repo_detail', repo_name=repo_name))

@app.route('/compare-repos')
def compare_repos():
    repo_names = request.args.getlist('repo')
    if not repo_names or len(repo_names) < 2:
        flash("Pilih minimal 2 repositori untuk dibandingkan.", "warning")
        return redirect(url_for('data_master', tab='git'))

    comparison_data = {}
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('data_master', tab='git'))

    try:
        cursor = conn.cursor(dictionary=True)
        for name in repo_names:
            cursor.execute("SELECT * FROM git_commits WHERE repo_name = %s", (name,))
            commits = cursor.fetchall()
            if commits:
                df_commits = pd.DataFrame(commits)
                stats = analyzer.analyze_git_data(df_commits)
                contribution = analyzer.analyze_team_contribution(df_commits)
                
                total_lines = 0
                for author, author_stats in contribution.items():
                    total_lines += author_stats.get('lines_added', 0)
                stats['total_lines_added'] = total_lines

                comparison_data[name] = stats
    except Exception as e:
        flash(f"Error saat menyiapkan data perbandingan: {e}", "danger")
        return redirect(url_for('data_master', tab='git'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('compare_repos.html', comparison_data=comparison_data, repo_names=repo_names)


@app.route('/delete/pdf/<int:doc_id>', methods=['POST'])
def delete_pdf(doc_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pdf_documents WHERE id = %s", (doc_id,))
            conn.commit()
            flash(f"Dokumen dengan ID {doc_id} berhasil dihapus.", "success")
        except Exception as e:
            flash(f"Gagal menghapus dokumen: {e}", "danger")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    return redirect(url_for('data_master', tab='pdf'))

@app.route('/delete/git/<path:repo_name>', methods=['POST'])
def delete_git_repo(repo_name):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM git_commits WHERE repo_name = %s", (repo_name,))
            cursor.execute("DELETE FROM git_issues WHERE repo_name = %s", (repo_name,))
            cursor.execute("DELETE FROM git_pull_requests WHERE repo_name = %s", (repo_name,))
            conn.commit()
            flash(f"Semua data untuk repositori {repo_name} berhasil dihapus.", "success")
        except Exception as e:
            flash(f"Gagal menghapus data repositori: {e}", "danger")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    return redirect(url_for('data_master', tab='git'))

@app.route('/reset-data', methods=['POST'])
def reset_data():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE pdf_documents;")
            cursor.execute("TRUNCATE TABLE git_commits;")
            cursor.execute("TRUNCATE TABLE git_issues;")
            cursor.execute("TRUNCATE TABLE git_pull_requests;")
            cursor.execute("TRUNCATE TABLE pdf_similarity;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            conn.commit()
            flash("Semua data di database telah berhasil dihapus.", "success")
        except Exception as e:
            flash(f"Gagal mereset data: {e}", "danger")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
