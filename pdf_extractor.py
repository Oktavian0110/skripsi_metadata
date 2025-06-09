import os
from PyPDF2 import PdfReader, PdfWriter
from datetime import datetime
from config import PDF_DIR, OUTPUT_DIR

def parse_pdf_date(pdf_date):
    try:
        date_str = pdf_date[2:16]  # Ambil YYYYMMDDHHMMSS
        return datetime.strptime(date_str, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except:
        return pdf_date

def extract_pdf_metadata(file_path):
    try:
        reader = PdfReader(file_path)
        meta = reader.metadata or {}
        file_name = os.path.basename(file_path)
        
        return {
            "judul": meta.get("/Title", file_name.replace(".pdf", "")),  # Pakai nama file jika judul kosong
            "author": meta.get("/Author", "Tidak Ditemukan"),
            "tanggal_modifikasi": parse_pdf_date(meta.get("/ModDate", "Tidak Diketahui")),
            "jumlah_halaman": len(reader.pages),
            "nama_file": file_name,
            "is_judul_generated": "/Title" not in meta  # True jika judul diambil dari nama file
        }
    except Exception as e:
        print(f"Error baca {file_path}: {e}")
        return None

def add_pdf_metadata(file_path, title, author):
    """Tambahkan metadata ke PDF jika kosong"""
    try:
        reader = PdfReader(file_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.add_metadata({
            "/Title": title,
            "/Author": author
        })

        with open(file_path, "wb") as f:
            writer.write(f)
        print(f"Metadata berhasil ditambahkan ke {file_path}")
    except Exception as e:
        print(f"Gagal menambah metadata: {e}")