import os
from PyPDF2 import PdfReader
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
        meta = reader.metadata
        return {
            "judul": meta.get("/Title", "Tidak ada"),
            "author": meta.get("/Author", "Tidak ada"),
            "tanggal_modifikasi": parse_pdf_date(meta.get("/ModDate", "Tidak ada")),
            "jumlah_halaman": len(reader.pages)
        }
    except Exception as e:
        print(f"Error baca {file_path}: {e}")
        return None

# Contoh penggunaan:
if __name__ == "__main__":
    pdf_path = os.path.join(PDF_DIR, "contoh_tugas.pdf")
    metadata = extract_pdf_metadata(pdf_path)
    print(metadata)