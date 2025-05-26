import pandas as pd
from pdf_extractor import extract_pdf_metadata
from git_extractor import extract_git_metadata
from config import OUTPUT_DIR

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(f"{OUTPUT_DIR}/{filename}", index=False)
    print(f"Data disimpan ke {OUTPUT_DIR}/{filename}")

def main():
    # 1. Ekstrak PDF
    pdf_data = extract_pdf_metadata("data/contoh_tugas.pdf")
    if pdf_data:
        save_to_csv([pdf_data], "pdf_metadata.csv")
    
    # 2. Ekstrak Git
    git_data = extract_git_metadata()
    if git_data:
        save_to_csv(git_data, "git_metadata.csv")

if __name__ == "__main__":
    main()