# app.py

import os
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for, flash
import pandas as pd
import math
from werkzeug.utils import secure_filename
import nltk

from pdf_extractor import PdfExtractor
from git_extractor import GitExtractor
from analyzer import Analyzer

# --- Unduh data NLTK yang diperlukan ---
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

# --- Konfigurasi Database ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'skripsi_metadata_db'
}

app = Flask(__name__)
app.secret_key = 'supersecretkey_yang_lebih_aman'

# --- Konfigurasi untuk Upload File ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inisialisasi global (tetap digunakan untuk rute lain yang tidak bermasalah)
pdf_extractor = PdfExtractor()
git_extractor = GitExtractor()
analyzer = Analyzer()

# --- Fungsi Database ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        flash(f"Error koneksi database: {err}", "danger")
        return None

def save_pdf_to_db(df):
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO pdf_documents (file_name, title, author, num_pages, creation_date, modification_date, keywords, word_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        for _, row in df.iterrows():
            keywords_list = row.get('keywords', [])
            keywords_str = ", ".join(keywords_list) if isinstance(keywords_list, list) else ""
            mod_date = row['modification_date'] if pd.notna(row['modification_date']) else None
            create_date = row['creation_date'] if pd.notna(row['creation_date']) else None
            word_count = int(row['word_count']) if pd.notna(row['word_count']) else 0
            cursor.execute(sql, (row['file_name'], row['title'], row['author'], int(row['num_pages']), create_date, mod_date, keywords_str, word_count))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving PDF data: {e}")
        return False
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
            sql_commits = "INSERT INTO git_commits (repo_name, commit_sha, commit_message, commit_author, commit_author_email, commit_date, category) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            for _, row in commits_df.iterrows():
                cursor.execute(sql_commits, (row['repo_name'], row['commit_sha'], row['commit_message'], row['commit_author'], row['commit_author_email'], row['commit_date'], row['category']))
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

# --- Fungsi Helper dengan Perbaikan ---
def analyze_and_save_pdfs(pdf_metadata_list, deadline=None):
    """Menganalisis list metadata PDF, menambahkan kata kunci, dan menyimpannya."""
    if not pdf_metadata_list:
        return False

    # PERBAIKAN: Buat instance Analyzer baru di sini untuk memastikan tidak ada state yang tersisa
    local_analyzer = Analyzer()
    
    df = pd.DataFrame(pdf_metadata_list)
    
    # Ekstrak kata kunci untuk setiap baris menggunakan instance lokal
    df['keywords'] = df['full_text'].apply(lambda text: local_analyzer.extract_keywords_from_text(text))
    
    # Hapus kolom full_text sebelum menyimpan untuk efisiensi database
    df_to_save = df.drop(columns=['full_text'])
    
    if save_pdf_to_db(df_to_save):
        if deadline:
            stats = local_analyzer.analyze_pdf_data(df.iloc[[0]], deadline)
            if stats.get('deadline_status'):
                flash(f"Status Pengumpulan: {stats['deadline_status']}", "info")
        return True
    else:
        return False

# --- Rute Aplikasi ---

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
                pdf_stats = {
                    'analyzed_filename': latest_pdf.get('file_name'),
                    'author_counts': {latest_pdf.get('author'): 1},
                    'avg_pages': latest_pdf.get('num_pages'),
                    'word_count': latest_pdf.get('word_count'),
                    'creation_date': latest_pdf.get('creation_date'),
                    'keywords': latest_pdf.get('keywords', '').split(',') if latest_pdf.get('keywords') else []
                }
            
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
    
    return render_template(
        'dashboard.html', 
        pdf_stats=pdf_stats, 
        git_stats=git_stats, 
        commits_over_time_data=commits_over_time_data,
        commit_category_chart_data=commit_category_chart_data
    )

@app.route('/data-master')
def data_master():
    context = { 'headers': [], 'data': [], 'total_pages': 1, 'current_page': request.args.get('page', 1, type=int), 'active_tab': request.args.get('tab', 'pdf') }
    conn = get_db_connection()
    if not conn:
        flash("Koneksi ke database gagal.", "danger")
        return render_template('data_master.html', **context)
    try:
        per_page = 10
        offset = (context['current_page'] - 1) * per_page
        cursor = conn.cursor(dictionary=True)
        if context['active_tab'] == 'pdf':
            count_query = "SELECT COUNT(*) as count FROM pdf_documents"
            context['headers'] = ["ID", "Nama File", "Judul", "Author", "Jml Halaman", "Waktu Analisis"]
            data_query = "SELECT id, file_name, title, author, num_pages, analysis_timestamp FROM pdf_documents ORDER BY analysis_timestamp DESC LIMIT %s OFFSET %s"
        elif context['active_tab'] == 'git':
            count_query = "SELECT COUNT(DISTINCT repo_name) as count FROM git_commits"
            context['headers'] = ["Nama Repositori", "Total Commit", "Kontributor", "Commit Terakhir"]
            data_query = "SELECT repo_name, COUNT(commit_sha) as total_commits, COUNT(DISTINCT commit_author) as contributors, MAX(commit_date) as last_commit FROM git_commits GROUP BY repo_name ORDER BY last_commit DESC LIMIT %s OFFSET %s"
        else:
            return redirect(url_for('data_master', tab='pdf'))
        cursor.execute(count_query)
        total_rows_result = cursor.fetchone()
        total_rows = total_rows_result['count'] if total_rows_result else 0
        context['total_pages'] = int(math.ceil(total_rows / per_page)) if total_rows > 0 else 1
        cursor.execute(data_query, (per_page, offset))
        context['data'] = cursor.fetchall()
    except Exception as e:
        print(f"Error in data_master: {e}")
        flash("Terjadi kesalahan saat memuat data master.", "danger")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('data_master.html', **context)

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
    return render_template('repo_detail.html', repo_name=repo_name, stats=git_stats, commits=commits)

@app.route('/pdf/<int:doc_id>')
def pdf_detail(doc_id):
    conn = get_db_connection()
    if not conn: return redirect(url_for('data_master', tab='pdf'))
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
    except Exception as e:
        flash(f"Error saat mengambil detail dokumen: {e}", "danger")
        return redirect(url_for('data_master', tab='pdf'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('pdf_detail.html', doc=doc)

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
                if file_extension == 'csv':
                    df_links = pd.read_csv(filepath)
                else:
                    df_links = pd.read_excel(filepath)
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
    repo_name = request.form.get('repo_name')
    deadline = request.form.get('deadline')
    if not repo_name:
        flash('Nama repositori tidak boleh kosong.', 'warning')
        return redirect(url_for('dashboard'))
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
