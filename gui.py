import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pdf_extractor import extract_pdf_metadata
from git_extractor import extract_git_metadata
import pandas as pd
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MetadataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Analisis Metadata PDF & Git")
        self.root.geometry("800x600")
        
        self.tab_control = ttk.Notebook(root)
        
        # Setup semua tab
        self.tab_pdf = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_pdf, text="PDF Metadata")
        self.setup_pdf_tab()
        
        self.tab_git = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_git, text="Git Metadata")
        self.setup_git_tab()
        
        self.tab_viz = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_viz, text="Visualisasi")
        self.setup_viz_tab()
        
        self.tab_control.pack(expand=1, fill="both")

        # Muat data awal saat aplikasi dibuka
        self.load_and_display_pdf_data()
        self.load_and_display_git_data()

    def setup_pdf_tab(self):
        # PERBAIKAN: Menggunakan .columnconfigure (tanpa _)
        self.tab_pdf.columnconfigure(1, weight=1)
        
        ttk.Label(self.tab_pdf, text="Pilih File PDF:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.pdf_path_entry = ttk.Entry(self.tab_pdf, width=60)
        self.pdf_path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ttk.Button(self.tab_pdf, text="Browse", command=self.browse_pdf).grid(row=0, column=2, padx=10, pady=10, sticky="e")
        
        button_frame = ttk.Frame(self.tab_pdf)
        button_frame.grid(row=1, column=1, pady=10)
        
        ttk.Button(button_frame, text="Ekstrak & Tambah Data", command=self.run_pdf_extraction).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Hapus Data Terpilih", command=self.delete_selected_pdf_row).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Hapus Semua Data PDF", command=lambda: self.clear_csv_file("pdf_metadata.csv", self.load_and_display_pdf_data)).pack(side="left", padx=5)
        
        self.pdf_results_frame = ttk.LabelFrame(self.tab_pdf, text="Data Tersimpan")
        self.pdf_results_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        # PERBAIKAN: Menggunakan .rowconfigure (tanpa _)
        self.tab_pdf.rowconfigure(2, weight=1)
        
    def setup_git_tab(self):
        # PERBAIKAN: Menggunakan .columnconfigure (tanpa _)
        self.tab_git.columnconfigure(1, weight=1)

        ttk.Label(self.tab_git, text="Nama Repository (format: user/repo):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.repo_entry = ttk.Entry(self.tab_git, width=60)
        self.repo_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.repo_entry.insert(0, "Oktavian0110/Alaskaki-Project")

        button_frame = ttk.Frame(self.tab_git)
        button_frame.grid(row=1, column=1, pady=10)
        
        ttk.Button(button_frame, text="Ekstrak & Tambah Data", command=self.run_git_extraction).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Hapus Data Terpilih", command=self.delete_selected_git_row).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Hapus Semua Data Git", command=lambda: self.clear_csv_file("git_metadata.csv", self.load_and_display_git_data)).pack(side="left", padx=5)
        
        self.git_results_frame = ttk.LabelFrame(self.tab_git, text="Data Tersimpan")
        self.git_results_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        # PERBAIKAN: Menggunakan .rowconfigure (tanpa _)
        self.tab_git.rowconfigure(2, weight=1)
        
    def browse_pdf(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filepath:
            self.pdf_path_entry.delete(0, tk.END)
            self.pdf_path_entry.insert(0, filepath)
    
    def run_pdf_extraction(self):
        filepath = self.pdf_path_entry.get()
        if not filepath: return messagebox.showerror("Error", "Pilih file PDF terlebih dahulu!")
        metadata = extract_pdf_metadata(filepath)
        if metadata:
            df_new = pd.DataFrame([metadata])
            csv_path = os.path.join("output", "pdf_metadata.csv")
            file_exists = os.path.exists(csv_path)
            df_new.to_csv(csv_path, mode='a', header=not file_exists, index=False)
            self.load_and_display_pdf_data()
            messagebox.showinfo("Sukses", "Data baru berhasil ditambahkan.")

    def run_git_extraction(self):
        repo_name = self.repo_entry.get()
        if not repo_name: return messagebox.showerror("Error", "Masukkan nama repository!")
        git_data = extract_git_metadata([repo_name])
        if git_data:
            df_new = pd.DataFrame(git_data)
            csv_path = os.path.join("output", "git_metadata.csv")
            file_exists = os.path.exists(csv_path)
            df_new.to_csv(csv_path, mode='a', header=not file_exists, index=False)
            self.load_and_display_git_data()
            messagebox.showinfo("Sukses", "Data baru berhasil ditambahkan.")

    def clear_csv_file(self, file_name, refresh_function):
        try:
            csv_path = os.path.join("output", file_name)
            if os.path.exists(csv_path):
                if messagebox.askyesno("Konfirmasi", f"Anda yakin ingin menghapus semua data di {file_name}?"):
                    os.remove(csv_path)
                    messagebox.showinfo("Sukses", f"Semua data di {file_name} telah dihapus.")
                    refresh_function()
            else:
                messagebox.showinfo("Info", "File data tidak ditemukan (sudah bersih).")
        except Exception as e: messagebox.showerror("Error", f"Gagal menghapus file: {e}")

    def load_and_display_pdf_data(self):
        for widget in self.pdf_results_frame.winfo_children(): widget.destroy()
        csv_path = os.path.join("output", "pdf_metadata.csv")
        if not os.path.exists(csv_path):
            ttk.Label(self.pdf_results_frame, text="Belum ada data.").pack(pady=20)
            return
        try:
            full_df = pd.read_csv(csv_path).reset_index(drop=True)
            cols = ("Nama File", "Judul", "Author", "Tanggal Modifikasi")
            tree = ttk.Treeview(self.pdf_results_frame, columns=cols, show="headings")
            for col in cols: tree.heading(col, text=col); tree.column(col, width=180)
            for index, row in full_df.iterrows():
                tree.insert("", "end", iid=index, values=(row["nama_file"], row["judul"], row["author"], row["tanggal_modifikasi"]))
            tree.pack(fill="both", expand=True)
        except Exception as e: ttk.Label(self.pdf_results_frame, text=f"Gagal memuat: {e}").pack(pady=20)

    def load_and_display_git_data(self):
        for widget in self.git_results_frame.winfo_children(): widget.destroy()
        csv_path = os.path.join("output", "git_metadata.csv")
        if not os.path.exists(csv_path):
            ttk.Label(self.git_results_frame, text="Belum ada data.").pack(pady=20)
            return
        try:
            full_df = pd.read_csv(csv_path).reset_index(drop=True)
            cols = ("Commit Hash", "Pesan", "Author", "Tanggal", "Kategori")
            tree = ttk.Treeview(self.git_results_frame, columns=cols, show="headings")
            for col in cols:
                tree.heading(col, text=col)
                if col == "Commit Hash": tree.column(col, width=80)
                elif col == "Pesan": tree.column(col, width=250)
                else: tree.column(col, width=110)
            for index, row in full_df.iterrows():
                short_hash = str(row.get("commit_hash", ""))[:7]
                tree.insert("", "end", iid=index, values=(short_hash, row["pesan"], row["author"], row["tanggal"], row.get("kategori", "N/A")))
            tree.pack(fill="both", expand=True)
        except Exception as e: ttk.Label(self.git_results_frame, text=f"Gagal memuat: {e}").pack(pady=20)
        
    def delete_selected_pdf_row(self):
        tree = self.pdf_results_frame.winfo_children()[0] if self.pdf_results_frame.winfo_children() else None
        if not isinstance(tree, ttk.Treeview): return messagebox.showerror("Error", "Tabel tidak ditemukan.")
        selected_items = tree.selection()
        if not selected_items: return messagebox.showwarning("Peringatan", "Pilih baris data untuk dihapus.")
        index_to_delete = int(selected_items[0])
        if messagebox.askyesno("Konfirmasi Hapus", "Anda yakin ingin menghapus baris data yang dipilih?"):
            try:
                csv_path = os.path.join("output", "pdf_metadata.csv"); df = pd.read_csv(csv_path)
                df = df.drop(index_to_delete)
                df.to_csv(csv_path, index=False)
                self.load_and_display_pdf_data()
                messagebox.showinfo("Sukses", "Data berhasil dihapus.")
            except Exception as e: messagebox.showerror("Error", f"Gagal menghapus data: {e}")

    def delete_selected_git_row(self):
        tree = self.git_results_frame.winfo_children()[0] if self.git_results_frame.winfo_children() else None
        if not isinstance(tree, ttk.Treeview): return messagebox.showerror("Error", "Tabel tidak ditemukan.")
        selected_items = tree.selection()
        if not selected_items: return messagebox.showwarning("Peringatan", "Pilih baris data untuk dihapus.")
        index_to_delete = int(selected_items[0])
        if messagebox.askyesno("Konfirmasi Hapus", "Anda yakin ingin menghapus baris data yang dipilih?"):
            try:
                csv_path = os.path.join("output", "git_metadata.csv"); df = pd.read_csv(csv_path)
                df = df.drop(index_to_delete)
                df.to_csv(csv_path, index=False)
                self.load_and_display_git_data()
                messagebox.showinfo("Sukses", "Data berhasil dihapus.")
            except Exception as e: messagebox.showerror("Error", f"Gagal menghapus data: {e}")
            
    def setup_viz_tab(self):
        button_frame = ttk.Frame(self.tab_viz); button_frame.pack(side="bottom", fill="x", pady=5)
        ttk.Button(button_frame, text="Grafik Author (Git)", command=self.show_commit_chart).pack(side="left", padx=5, pady=5, expand=True)
        ttk.Button(button_frame, text="Grafik Kategori (Git)", command=self.show_category_chart).pack(side="left", padx=5, pady=5, expand=True)
        ttk.Button(button_frame, text="Grafik Author (PDF)", command=self.show_pdf_chart).pack(side="left", padx=5, pady=5, expand=True)
        self.viz_frame = ttk.LabelFrame(self.tab_viz, text="Kanvas Grafik"); self.viz_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas = None

    def show_commit_chart(self):
        try:
            csv_path = os.path.join("output", "git_metadata.csv")
            if not os.path.exists(csv_path): return messagebox.showerror("Error", "File git_metadata.csv tidak ditemukan.")
            df = pd.read_csv(csv_path)
            if df.empty: return messagebox.showinfo("Info", "Tidak ada data untuk ditampilkan.")
            commit_counts = df.groupby('author').size()
            if self.canvas: self.canvas.get_tk_widget().destroy()
            fig = Figure(figsize=(7, 5), dpi=100); ax = fig.add_subplot(111)
            commit_counts.plot(kind='bar', ax=ax, color='skyblue'); ax.set_title("Jumlah Commit per Author"); ax.set_ylabel("Jumlah Commit"); ax.set_xlabel("Author")
            ax.tick_params(axis='x', rotation=45); fig.tight_layout()
            self.canvas = FigureCanvasTkAgg(fig, master=self.viz_frame); self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e: messagebox.showerror("Error", f"Gagal membuat grafik: {e}")

    def show_pdf_chart(self):
        try:
            csv_path = os.path.join("output", "pdf_metadata.csv")
            if not os.path.exists(csv_path): return messagebox.showerror("Error", "File pdf_metadata.csv tidak ditemukan.")
            df = pd.read_csv(csv_path)
            if df.empty: return messagebox.showinfo("Info", "Tidak ada data PDF untuk ditampilkan.")
            author_counts = df.groupby('author').size()
            if self.canvas: self.canvas.get_tk_widget().destroy()
            fig = Figure(figsize=(7, 5), dpi=100); ax = fig.add_subplot(111)
            ax.pie(author_counts, labels=author_counts.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal'); ax.set_title("Distribusi Dokumen per Author"); fig.tight_layout()
            self.canvas = FigureCanvasTkAgg(fig, master=self.viz_frame); self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e: messagebox.showerror("Error", f"Gagal membuat grafik: {e}")

    def show_category_chart(self):
        try:
            csv_path = os.path.join("output", "git_metadata.csv")
            if not os.path.exists(csv_path): return messagebox.showerror("Error", "File git_metadata.csv tidak ditemukan.")
            df = pd.read_csv(csv_path)
            if df.empty or 'kategori' not in df.columns:
                return messagebox.showinfo("Info", "Tidak ada data kategori untuk ditampilkan.")
            
            category_counts = df.groupby('kategori').size()
            if self.canvas: self.canvas.get_tk_widget().destroy()
            
            fig = Figure(figsize=(7, 5), dpi=100); ax = fig.add_subplot(111)
            category_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%', startangle=90, wedgeprops=dict(width=0.3))
            ax.axis('equal'); ax.set_title("Distribusi Kategori Commit"); ax.set_ylabel('')
            
            self.canvas = FigureCanvasTkAgg(fig, master=self.viz_frame); self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuat grafik kategori: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataApp(root)
    root.mainloop()