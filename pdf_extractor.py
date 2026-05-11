import logging
# pdf_extractor.py

import os
import gdown
import shutil # <--- Pindahkan ke atas
import glob   # <--- Pindahkan ke atas
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
            logging.error(f"Error membaca file PDF {os.path.basename(file_path)}: {e}")
            return None

    def extract_metadata_from_gdrive_links(self, links):
        """Menerima list link, mengunduh via gdown dengan nama asli, dan mengekstrak metadata."""
        if not links:
            return ('invalid_link', [])
        
        link = links[0] 
        downloaded_file = None
        
        try:
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
            logging.error(f"Gagal memproses link {link}: {e}")
            return ('download_error', [])
            
        finally:
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
            logging.error(f"Error mengekstrak file lokal {os.path.basename(file_path)}: {e}")
            return ('unknown_error', [])    
        
    def extract_metadata_from_gdrive_folder(self, folder_url):
        """Mendownload folder GDrive, mengekstrak semua PDF di dalamnya."""
        output_folder = 'temp_gdrive_folder'
        
        # Buat/Bersihkan folder temp
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)

        try:
            # Download seluruh folder
            gdown.download_folder(url=folder_url, output=output_folder, quiet=False, use_cookies=False)
            
            metadata_list = []
            # Cari semua file .pdf di dalam folder yang didownload
            pdf_files = glob.glob(f"{output_folder}/**/*.pdf", recursive=True)
            
            for file_path in pdf_files:
                meta = self._extract_single_pdf_metadata(file_path)
                if meta:
                    metadata_list.append(meta)
                    
            return ('success', metadata_list)
        except Exception as e:
            logging.error(f"Gagal memproses folder {folder_url}: {e}")
            return ('download_error', [])
        finally:
            # Bersihkan folder sampah setelah selesai
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)