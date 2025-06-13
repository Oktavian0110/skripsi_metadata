# app.py

# 1. Tambahkan secure_filename untuk keamanan
from flask import Flask, jsonify, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import os

from git_extractor import extract_git_metadata
from pdf_extractor import extract_pdf_metadata

app = Flask(__name__)

# 2. Konfigurasi folder untuk menyimpan file upload
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Pastikan folder 'uploads' ada


def get_data_from_csv(file_name):
    # ... (fungsi ini tidak berubah) ...
    csv_path = os.path.join("output", file_name)
    if not os.path.exists(csv_path): return None
    try:
        df = pd.read_csv(csv_path); return df.to_dict(orient='records')
    except Exception as e:
        print(f"Error membaca CSV {file_name}: {e}"); return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add-repo', methods=['POST'])
def add_repo():
    # ... (fungsi ini tidak berubah) ...
    repo_name = request.form.get('repo_name')
    if repo_name and '/' in repo_name:
        new_data = extract_git_metadata([repo_name])
        if new_data:
            df_new = pd.DataFrame(new_data)
            csv_path = os.path.join("output", "git_metadata.csv")
            file_exists = os.path.exists(csv_path)
            df_new.to_csv(csv_path, mode='a', header=not file_exists, index=False)
    return redirect(url_for('index'))

# --- RUTE BARU UNTUK MENANGANI UPLOAD FILE PDF ---
@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    # Periksa apakah ada file di dalam request
    if 'pdf_file' not in request.files:
        return redirect(url_for('index')) # Kembali jika tidak ada file

    file = request.files['pdf_file']

    # Periksa apakah pengguna tidak memilih file
    if file.filename == '':
        return redirect(url_for('index'))
    
    # Jika ada file dan merupakan file PDF
    if file and file.filename.endswith('.pdf'):
        # Amankan nama file untuk mencegah hacking
        filename = secure_filename(file.filename)
        # Buat path lengkap untuk menyimpan file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Simpan file ke server
        file.save(filepath)

        # Ekstrak metadata dari file yang baru saja di-upload
        metadata = extract_pdf_metadata(filepath)
        if metadata:
            df_new = pd.DataFrame([metadata])
            csv_path = os.path.join("output", "pdf_metadata.csv")
            file_exists = os.path.exists(csv_path)
            df_new.to_csv(csv_path, mode='a', header=not file_exists, index=False)
            
    # Kembalikan pengguna ke halaman utama setelah selesai
    return redirect(url_for('index'))


# --- API Endpoints (tidak ada perubahan) ---
@app.route('/api/git')
def get_git_data():
    # ... (fungsi ini tidak berubah) ...
    data = get_data_from_csv("git_metadata.csv");
    if data is not None: return jsonify(data)
    else: return jsonify({"error": "Data Git tidak ditemukan."}), 404

@app.route('/api/pdf')
def get_pdf_data():
    # ... (fungsi ini tidak berubah) ...
    data = get_data_from_csv("pdf_metadata.csv")
    if data is not None: return jsonify(data)
    else: return jsonify({"error": "Data PDF tidak ditemukan."}), 404

if __name__ == '__main__':
    app.run(debug=True)