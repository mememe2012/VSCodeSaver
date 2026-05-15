import os
import shutil
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import threading
from pathlib import Path

VSCODE_USER_DIR = Path(os.environ['APPDATA']) / 'Code' / 'User'
SETTINGS_FILE = VSCODE_USER_DIR / 'settings.json'
KEYBINDINGS_FILE = VSCODE_USER_DIR / 'keybindings.json'
LOCALE_FILE = VSCODE_USER_DIR / 'locale.json'
SNIPPETS_DIR = VSCODE_USER_DIR / 'snippets'
GLOBAL_STORAGE_DIR = VSCODE_USER_DIR / 'globalStorage'
WORKSPACE_STORAGE_DIR = VSCODE_USER_DIR / 'workspaceStorage'
EXTENSIONS_DIRS = [
    Path.home() / '.vscode' / 'extensions',
    VSCODE_USER_DIR.parent / 'extensions'
]
SAVES_DIR = Path('saves')

class VSCodeSaverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VSCode 配置管理器")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        title_label = tk.Label(root, text="VSCode 配置管理器", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        save_button = tk.Button(root, text="保存当前配置", command=self.save_config, font=("Arial", 12))
        save_button.pack(pady=10)

        load_label = tk.Label(root, text="选择保存配置加载:", font=("Arial", 12))
        load_label.pack(pady=5)

        self.save_listbox = tk.Listbox(root, height=10, font=("Arial", 10))
        self.save_listbox.pack(pady=5, fill=tk.BOTH, expand=True)

        load_button = tk.Button(root, text="加载选中配置", command=self.load_config, font=("Arial", 12))
        load_button.pack(pady=10)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        self.status_label = tk.Label(root, text="", font=("Arial", 10))
        self.status_label.pack(pady=5)

        self.update_save_list()

    def update_save_list(self):
        self.save_listbox.delete(0, tk.END)
        if SAVES_DIR.exists():
            for save in SAVES_DIR.glob('*.zip'):
                self.save_listbox.insert(tk.END, save.stem)

    def save_config(self):
        name = simpledialog.askstring("保存配置", "输入保存名称:")
        if not name:
            return

        if not VSCODE_USER_DIR.exists():
            messagebox.showerror("错误", "VSCode用户目录不存在！")
            return

        SAVES_DIR.mkdir(exist_ok=True)
        zip_path = SAVES_DIR / f"{name}.zip"

        save_sources = []
        if SETTINGS_FILE.exists():
            save_sources.append((SETTINGS_FILE, Path('user')))
        if KEYBINDINGS_FILE.exists():
            save_sources.append((KEYBINDINGS_FILE, Path('user')))
        if LOCALE_FILE.exists():
            save_sources.append((LOCALE_FILE, Path('user')))
        if SNIPPETS_DIR.exists():
            save_sources.append((SNIPPETS_DIR, Path('user/snippets')))
        if GLOBAL_STORAGE_DIR.exists():
            save_sources.append((GLOBAL_STORAGE_DIR, Path('user/globalStorage')))
        if WORKSPACE_STORAGE_DIR.exists():
            save_sources.append((WORKSPACE_STORAGE_DIR, Path('user/workspaceStorage')))
        for ext_dir in EXTENSIONS_DIRS:
            if ext_dir.exists():
                root_name = 'extensions' if ext_dir == EXTENSIONS_DIRS[0] else f'extensions_{ext_dir.name}'
                save_sources.append((ext_dir, Path(root_name)))

        files_to_zip = []
        for source_path, arc_root in save_sources:
            if source_path.is_file():
                files_to_zip.append((source_path, arc_root / source_path.name))
            else:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = Path(root) / file
                        files_to_zip.append((file_path, arc_root / file_path.relative_to(source_path)))

        total_files = len(files_to_zip)
        if total_files == 0:
            messagebox.showwarning("警告", "没有找到配置、插件或插件配置文件！")
            return

        self.progress['maximum'] = total_files
        self.progress['value'] = 0
        self.status_label.config(text="正在保存...")

        def save_thread():
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for i, (file_path, arcname) in enumerate(files_to_zip):
                    zipf.write(file_path, arcname)
                    self.progress['value'] = i + 1
                    self.root.update_idletasks()
            self.status_label.config(text="保存完成！")
            self.update_save_list()
            messagebox.showinfo("成功", f"配置已保存到 {zip_path}")

        threading.Thread(target=save_thread).start()

    def load_config(self):
        selection = self.save_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个保存配置！")
            return

        name = self.save_listbox.get(selection[0])
        zip_path = SAVES_DIR / f"{name}.zip"
        if not zip_path.exists():
            messagebox.showerror("错误", "保存文件不存在！")
            return

        with zipfile.ZipFile(zip_path, 'r') as zipf:
            file_list = zipf.namelist()
            total_files = len(file_list)

        self.progress['maximum'] = total_files
        self.progress['value'] = 0
        self.status_label.config(text="正在加载...")

        def load_thread():
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                for i, file_name in enumerate(file_list):
                    member_path = Path(file_name)
                    root_folder = member_path.parts[0]
                    relative_path = member_path.relative_to(root_folder)
                    if root_folder == 'user':
                        dest_base = VSCODE_USER_DIR
                    elif root_folder.startswith('extensions'):
                        if root_folder == 'extensions':
                            dest_base = EXTENSIONS_DIRS[0]
                        else:
                            dest_base = next((d for d in EXTENSIONS_DIRS if d.name == root_folder[len('extensions_'):]), EXTENSIONS_DIRS[0])
                    else:
                        dest_base = VSCODE_USER_DIR

                    dest_path = dest_base / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with zipf.open(file_name) as source, open(dest_path, 'wb') as target:
                        target.write(source.read())
                    self.progress['value'] = i + 1
                    self.root.update_idletasks()
            self.status_label.config(text="加载完成！请重启VSCode以应用更改。")
            messagebox.showinfo("成功", f"配置 {name} 已加载。请重启VSCode。")

        threading.Thread(target=load_thread).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = VSCodeSaverApp(root)
    root.mainloop()
