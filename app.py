# app.py

import os
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for, flash
import pandas as pd
import math

from pdf_extractor import PdfExtractor
from git_extractor import GitExtractor
from analyzer import Analyzer
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'supersecretkey_yang_lebih_aman'

# Inisialisasi
pdf_extractor = PdfExtractor()
git_extractor = GitExtractor()
analyzer = Analyzer()

# --- Fungsi Database ---
# ... (Fungsi-fungsi database tidak berubah) ...
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
        sql = "INSERT INTO pdf_documents (file_name, title, author, num_pages, modification_date, keywords) VALUES (%s, %s, %s, %s, %s, %s)"
        for _, row in df.iterrows():
            keywords_str = ", ".join(row.get('keywords', []))
            mod_date = row['modification_date'] if pd.notna(row['modification_date']) else None
            cursor.execute(sql, (row['file_name'], row['title'], row['author'], int(row['num_pages']), mod_date, keywords_str))
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

# --- Rute Aplikasi ---
@app.route('/')
def dashboard():
    # ... (Logika dashboard tidak berubah) ...
    pdf_stats, git_stats = {}, {}
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM pdf_documents ORDER BY analysis_timestamp DESC LIMIT 1")
            latest_pdf = cursor.fetchone()
            if latest_pdf:
                pdf_stats = {'total_files': 1, 'avg_pages': latest_pdf['num_pages'], 'author_counts': {latest_pdf['author']: 1}, 'keywords': latest_pdf['keywords'].split(', ') if latest_pdf['keywords'] else [], 'analyzed_filename': latest_pdf['file_name']}
            
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
                    git_stats['total_issues'] = cursor.fetchone()['count']
                    cursor.execute("SELECT COUNT(*) as count FROM git_pull_requests WHERE repo_name = %s", (repo_name,))
                    git_stats['total_pull_requests'] = cursor.fetchone()['count']
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    commit_category_chart_data = git_stats.get('commit_category_counts', {})
    commits_over_time_data = git_stats.get('commits_over_time', {})
    
    return render_template('dashboard.html', pdf_stats=pdf_stats, git_stats=git_stats, commit_category_chart_data=commit_category_chart_data, commits_over_time_data=commits_over_time_data)

@app.route('/data-master')
def data_master():
    # ... (Logika data_master tidak berubah) ...
    context = {
        'headers': [], 'data': [], 'total_pages': 1,
        'current_page': request.args.get('page', 1, type=int),
        'active_tab': request.args.get('tab', 'pdf')
    }
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
            context['headers'] = ["ID", "Nama File", "Judul", "Author", "Jml Halaman", "Kata Kunci", "Waktu Analisis"]
            data_query = "SELECT id, file_name, title, author, num_pages, keywords, analysis_timestamp FROM pdf_documents ORDER BY analysis_timestamp DESC LIMIT %s OFFSET %s"
        elif context['active_tab'] == 'commits':
            count_query = "SELECT COUNT(*) as count FROM git_commits"
            context['headers'] = ["ID", "Repo", "Author", "Pesan", "Kategori", "Tanggal"]
            data_query = "SELECT id, repo_name, commit_author, commit_message, category, commit_date FROM git_commits ORDER BY commit_date DESC LIMIT %s OFFSET %s"
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

# --- Rute untuk Proses Data ---
@app.route('/analyze-pdf', methods=['POST'])
def analyze_pdf():
    link = request.form.get('gdrive_link')
    deadline = request.form.get('deadline') # Ambil nilai deadline

    if not link:
        flash('Link Google Drive tidak boleh kosong.', 'warning')
        return redirect(url_for('dashboard'))

    status, pdf_metadata_list = pdf_extractor.extract_metadata_from_gdrive_links([link])
    
    if status == 'success':
        df = pd.DataFrame(pdf_metadata_list)
        # Lakukan analisis deadline
        pdf_stats = analyzer.analyze_pdf_data(df, deadline)
        
        # Simpan ke DB
        if save_pdf_to_db(df):
            flash('Dokumen berhasil dianalisis dan disimpan.', 'success')
        
        # Tampilkan hasil deadline jika ada
        if pdf_stats.get('deadline_status'):
            flash(f"Status Pengumpulan: {pdf_stats['deadline_status']}", "info")
            
    elif status == 'private':
        flash("Gagal: File bersifat privat. Ubah setelan berbagi.", "danger")
    else:
        flash("Gagal mengekstrak metadata dari link.", "danger")

    return redirect(url_for('dashboard'))

@app.route('/analyze-git', methods=['POST'])
def analyze_git():
    repo_name = request.form.get('repo_name')
    deadline = request.form.get('deadline')

    if not repo_name:
        flash('Nama repositori tidak boleh kosong.', 'warning')
        return redirect(url_for('dashboard'))

    commits_df, issues_df, prs_df = git_extractor.extract_git_metadata(repo_name)
    
    if commits_df.empty and issues_df.empty and prs_df.empty:
        flash(f'Gagal mengambil data dari repositori "{repo_name}".', 'danger')
    else:
        if save_git_data_to_db(commits_df, issues_df, prs_df):
            flash(f'Data untuk repositori "{repo_name}" berhasil disimpan.', 'success')

        if deadline and not commits_df.empty:
            deadline_stats = analyzer.analyze_git_data(commits_df, deadline)
            flash(f"Hasil Analisis Deadline: Tepat Waktu: {deadline_stats['on_time_commits']} commit, Terlambat: {deadline_stats['late_commits']} commit.", "info")

    return redirect(url_for('dashboard'))

@app.route('/reset-data', methods=['POST'])
def reset_data():
    # ... (Logika reset_data tidak berubah) ...
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE pdf_documents;")
        cursor.execute("TRUNCATE TABLE git_commits;")
        cursor.execute("TRUNCATE TABLE git_issues;")
        cursor.execute("TRUNCATE TABLE git_pull_requests;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        cursor.close()
        conn.close()
        flash("Semua data di database telah berhasil dihapus.", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
