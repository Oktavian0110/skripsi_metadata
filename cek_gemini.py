import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Muat API Key dari .env
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

print(f"API Key terdeteksi: {api_key[:10]}... (disembunyikan)")

if not api_key:
    print("ERROR: API Key tidak ditemukan. Cek file .env kamu!")
    exit()

# 2. Konfigurasi Gemini
genai.configure(api_key=api_key)

try:
    print("\n[DAFTAR MODEL YANG TERSEDIA UNTUK API KEY INI]")
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            available_models.append(m.name)
            
    if not available_models:
        print("ERROR: Tidak ada model yang mendukung generateContent di akunmu.")
        exit()

    # 3. Mari kita coba pakai model pertama yang ada di daftar
    model_to_use = available_models[0].replace('models/', '') # ambil model pertama
    print(f"\n>> Mencoba mengirim pesan test ke model: {model_to_use} ...")
    
    model = genai.GenerativeModel(model_to_use)
    response = model.generate_content("Halo, apakah kamu bisa merespon pesan ini?")
    
    print("\n[RESPON DARI GEMINI]")
    print(response.text)
    print("\n>>> SUKSES! API KEY DAN LIBRARY NORMAL <<<")

except Exception as e:
    print(f"\n[ERROR DETAIL]")
    print(e)