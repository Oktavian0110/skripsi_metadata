import pandas as pd
from pdf_extractor import extract_pdf_metadata, add_pdf_metadata
from git_extractor import extract_git_metadata
from config import PDF_DIR, OUTPUT_DIR
import os
from datetime import datetime  # ← Tambahan untuk timestamp

def save_to_csv(data, filename_prefix):
    df = pd.DataFrame(data)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate nama file dengan timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"

    # Simpan file CSV
    df.to_csv(os.path.join(OUTPUT_DIR, filename), index=False, encoding="utf-8")
    print(f"Data disimpan ke {OUTPUT_DIR}/{filename}")

def main():
    # 1. Ekstrak metadata Git
    git_data = extract_git_metadata()
    if git_data:
        save_to_csv(git_data, "git_metadata")
        print("Contoh data Git:")
        print(git_data[0])  # Tampilkan sample data pertama

    # 2. Ekstrak metadata PDF
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    pdf_data = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        metadata = extract_pdf_metadata(pdf_path)
        if metadata:
            pdf_data.append(metadata)

            # Tambahkan metadata jika judul masih default
            if metadata["is_judul_generated"]:
                add_pdf_metadata(pdf_path, metadata["judul"], metadata["author"])

    if pdf_data:
        save_to_csv(pdf_data, "pdf_metadata")
        print("\nContoh data PDF:")
        print(pdf_data[0])

if __name__ == "__main__":
    main()
