# pdf_extractor.py

import os
import re
import requests
import tempfile
from PyPDF2 import PdfReader
from datetime import datetime
import pandas as pd

class PdfExtractor:
    """
    A class to extract metadata and full text from PDF documents via Google Drive links.
    """
    def _get_gdrive_download_url(self, gdrive_url):
        """Converts a Google Drive sharing URL to a direct download link."""
        file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', gdrive_url)
        if file_id_match:
            file_id = file_id_match.group(1)
            return f'https://drive.google.com/uc?export=download&id={file_id}'
        return None

    def _extract_single_pdf_metadata(self, file_path):
        """Extracts metadata and full text from a single local PDF file."""
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

            author = meta.author or "Unknown"
            title = meta.title or "Unknown"
            num_pages = len(reader.pages)
            
            mod_date = None
            if meta.modification_date:
                mod_date = meta.modification_date.replace(tzinfo=None)

            metadata = {
                'file_name': os.path.basename(file_path),
                'title': title,
                'author': author,
                'num_pages': num_pages,
                'modification_date': mod_date,
                'full_text': full_text
            }
            return metadata
        except Exception as e:
            print(f"Error reading PDF file {os.path.basename(file_path)}: {e}")
            return None

    def extract_metadata_from_gdrive_links(self, links):
        """
        Downloads a PDF from a GDrive link and extracts metadata.
        Returns a tuple: (status, data)
        status can be 'success', 'private', 'invalid_link', or 'download_error'.
        """
        if not links:
            return ('invalid_link', [])
            
        link = links[0] 
        temp_filepath = None
        try:
            download_url = self._get_gdrive_download_url(link)
            if not download_url:
                return ('invalid_link', [])

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # --- LOGIKA BARU: Cek jika Google mengembalikan halaman HTML (tanda file privat) ---
            if 'text/html' in response.headers.get('Content-Type', ''):
                return ('private', [])

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                temp_pdf.write(response.content)
                temp_filepath = temp_pdf.name
            
            metadata = self._extract_single_pdf_metadata(temp_filepath)
            if metadata:
                return ('success', [metadata])
            else:
                return ('processing_error', [])

        except requests.exceptions.RequestException as e:
            print(f"Failed to download from {link}: {e}")
            return ('download_error', [])
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        return ('unknown_error', [])
