import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class CriteriaScore(BaseModel):
    kriteria: str = Field(description="Nama kriteria yang dinilai")
    penjelasan: str = Field(description="Penjelasan detail MENGAPA skor ini diberikan, merujuk langsung pada rubrik.")
    nilai: float = Field(description="Skor angka untuk kriteria tersebut")

class EvaluationResult(BaseModel):
    analisis_umum: str = Field(description="Langkah 1: Tuliskan analisis umum mengenai kualitas dokumen secara objektif sebelum memberi skor.")
    criteria_scores: list[CriteriaScore] = Field(description="Langkah 2: Rincian skor dan penjelasan wajib untuk masing-masing kriteria.")
    total_score: float = Field(description="Langkah 3: Kalkulasi total skor keseluruhan.")
    feedback: str = Field(description="Langkah 4: Kesimpulan feedback akhir untuk mahasiswa.")

class AIGrader:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logging.warning("GEMINI_API_KEY tidak ditemukan di .env")
        
        self.client = genai.Client(api_key=api_key)
        # Menggunakan gemini-2.5-flash-lite karena versi ini jauh lebih ringan
        # dan memiliki limit (kuota) harian yang jauh lebih besar dari versi standar/Pro.
        self.model_name = 'gemini-2.5-flash-lite'

    def grade_document(self, rubric_text, student_text):
        if not student_text or len(student_text.strip()) < 10:
            logging.warning("Teks dokumen mahasiswa kosong atau tidak terbaca (Mungkin PDF Scan).")
            return None
            
        if not rubric_text:
            logging.warning("Teks rubrik kosong.")
            return None

        prompt = f"""
        Kamu adalah asisten dosen ahli yang bertugas menilai dokumen tugas skripsi mahasiswa.
        Tugas utamamu adalah memberikan penilaian yang KONSISTEN, OBJEKTIF, dan SANGAT KETAT terhadap rubrik.
        
        Berikut adalah RUBRIK PENILAIAN:
        ---
        {rubric_text}
        ---
        
        Berikut adalah DOKUMEN MAHASISWA:
        ---
        {student_text}
        ---
        
        INSTRUKSI EVALUASI:
        1. Jangan menebak-nebak. Jika informasi tidak ada di dokumen mahasiswa, berikan skor rendah.
        2. Analisis terlebih dahulu kecocokan dokumen dengan setiap kriteria di rubrik.
        3. Jelaskan alasanmu secara rinci SEBELUM memberikan angka. Ini penting agar penilaianmu konsisten.
        4. WAJIB: Konversikan kalkulasi skor total akhir menjadi skala persentase 0 - 100 (misal: jika rubrik memakai skala 1-4 dan mahasiswa mendapat nilai sempurna 4, maka total_score adalah 100).
        """
        
        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logging.info(f">> Sedang mengirim dokumen ke Gemini AI... (Percobaan {attempt+1})")
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EvaluationResult,
                        temperature=0.0, 
                    ),
                )
                
                result = json.loads(response.text)
                
                criteria_dict = {item['kriteria']: item['nilai'] for item in result.get('criteria_scores', [])}
                
                detailed_feedback = "**Analisis Umum:**\n" + result.get('analisis_umum', '') + "\n\n"
                detailed_feedback += "**Catatan per Kriteria:**\n"
                for item in result.get('criteria_scores', []):
                    detailed_feedback += f"- **{item['kriteria']}**: {item.get('penjelasan', '')}\n"
                detailed_feedback += "\n**Kesimpulan:**\n" + result.get('feedback', '')

                result['criteria_scores'] = criteria_dict
                result['feedback'] = detailed_feedback
                
                logging.info(f"Berhasil menilai dokumen. Total Skor: {result.get('total_score')}")
                return result

            except Exception as e:
                error_msg = str(e)
                if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
                    if attempt < max_retries - 1:
                        logging.warning(f"API Limit Tercapai (429). Menunggu 32 detik sebelum mencoba lagi...")
                        time.sleep(32)
                        continue
                logging.error(f"ERROR saat AI menilai: {e}")
                return None