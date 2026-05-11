# pdf_extractor.py

import os
import gdown
from PyPDF2 import PdfReader
import pandas as pd

class PdfExtractor:
    """
    Mengekstrak metadata dan teks lengkap dari dokumen PDF.
    Menggunakan gdown untuk menangani link Google Drive dan mendeteksi nama file asli.
    """

    def _extract_single_pdf_metadata(self, file_path):
        """Mengekstrak metadata dari satu file PDF lokal."""
        try:
            reader = PdfReader(file_path)
            meta = reader.metadata
            
            full_text = ""
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                except Exception:
                    continue

            # Ambil nama file asli dari path
            filename = os.path.basename(file_path)

            metadata = {
                'file_name': filename,  # <--- Ini sekarang akan mengambil nama asli
                'title': meta.title if meta and meta.title else "Unknown",
                'author': meta.author if meta and meta.author else "Unknown",
                'num_pages': len(reader.pages),
                'creation_date': meta.creation_date if meta else None,
                'modification_date': meta.modification_date if meta else None,
                'full_text': full_text,
                'word_count': len(full_text.split())
            }
            return metadata
        except Exception as e:
            print(f"Error membaca file PDF {os.path.basename(file_path)}: {e}")
            return None

    def extract_metadata_from_gdrive_links(self, links):
        """Menerima list link, mengunduh via gdown dengan nama asli, dan mengekstrak metadata."""
        if not links:
            return ('invalid_link', [])
        
        link = links[0] 
        downloaded_file = None
        
        try:
            # --- PERBAIKAN: Hapus tempfile ---
            # Biarkan gdown mendownload ke folder saat ini agar nama aslinya terdeteksi
            downloaded_file = gdown.download(link, quiet=True, fuzzy=True)
            
            # Cek apakah download berhasil
            if not downloaded_file or not os.path.exists(downloaded_file):
                 return ('download_error', [])

            # Cek apakah file kosong
            if os.path.getsize(downloaded_file) == 0:
                return ('download_error', [])

            # Cek Header PDF (Untuk memastikan bukan file HTML/Login page)
            with open(downloaded_file, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    # Jika bukan PDF, hapus dan return private
                    return ('private', [])

            # Ekstrak metadata (sekarang downloaded_file memiliki nama asli)
            metadata = self._extract_single_pdf_metadata(downloaded_file)
            
            if metadata:
                return ('success', [metadata])
            else:
                return ('processing_error', [])

        except Exception as e:
            print(f"Gagal memproses link {link}: {e}")
            return ('download_error', [])
            
        finally:
            # --- PENTING: Bersihkan File ---
            # Karena kita mendownload ke folder aplikasi, kita WAJIB menghapusnya setelah selesai
            # agar server tidak penuh sampah file PDF.
            if downloaded_file and os.path.exists(downloaded_file):
                try:
                    os.remove(downloaded_file)
                except PermissionError:
                    pass 
                    
        return ('unknown_error', [])

    def extract_metadata_from_local_file(self, file_path):
        """Wrapper untuk file lokal."""
        try:
            metadata = self._extract_single_pdf_metadata(file_path)
            if metadata:
                return ('success', [metadata])
            else:
                return ('processing_error', [])
        except Exception as e:
            print(f"Error mengekstrak file lokal {os.path.basename(file_path)}: {e}")
            return ('unknown_error', [])    