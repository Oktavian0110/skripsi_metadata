# app.py

# 1. Tambahkan 'render_template' ke dalam import
from flask import Flask, jsonify, render_template
import pandas as pd
import os

app = Flask(__name__)

def get_data_from_csv(file_name):
    # ... (fungsi ini tidak berubah) ...
    csv_path = os.path.join("output", file_name)
    if not os.path.exists(csv_path): return None
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Error membaca CSV {file_name}: {e}")
        return None

# --- PERUBAHAN DI SINI ---
# 2. Ubah fungsi index() untuk menyajikan file HTML
@app.route('/')
def index():
    # render_template akan mencari file 'index.html' di dalam folder 'templates'
    return render_template('index.html')

@app.route('/api/git')
def get_git_data():
    # ... (fungsi ini tidak berubah) ...
    data = get_data_from_csv("git_metadata.csv")
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