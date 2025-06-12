# analyzer.py
# Definisikan kata kunci untuk setiap kategori.
KATEGORI_KEYWORDS = {
    'Fitur Baru': ['add', 'tambah', 'feature', 'buat', 'implementasi', 'implement'],
    'Perbaikan Bug': ['fix', 'bug', 'perbaiki', 'patch', 'hotfix', 'error'],
    'Dokumentasi': ['docs', 'doc', 'dokumentasi', 'readme', 'update readme'],
    'Refactor': ['refactor', 'cleanup', 'restructure', 'optimasi', 'optim', 'style']
}

def kategorikan_commit(message):
    """
    Menganalisis sebuah pesan commit dan mengembalikannya ke dalam sebuah kategori.
    """
    # Memastikan pesan adalah string
    if not isinstance(message, str):
        return 'Lainnya'

    # Ubah pesan ke huruf kecil agar pencocokan tidak sensitif huruf besar/kecil
    lower_message = message.lower()

    # Cek setiap kategori dan kata kuncinya
    for category, keywords in KATEGORI_KEYWORDS.items():
        for keyword in keywords:
            # Jika salah satu kata kunci ditemukan dalam pesan, kembalikan kategorinya
            if keyword in lower_message:
                return category
    
    # Jika setelah semua pengecekan tidak ada kata kunci yang cocok,
    # kembalikan kategori default 'Lainnya'
    return 'Lainnya'