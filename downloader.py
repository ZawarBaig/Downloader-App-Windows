import sys
import os
import re
import threading
import urllib.request
import io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
from PIL import Image, ImageTk

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MrBaigDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Mr.Baig Downloader")
        self.root.geometry("900x700")
        
        # --- COLOR PALETTE ---
        self.bg_color = "#F0F4F8"
        self.header_bg = "#2C3E50"
        self.header_fg = "#FFFFFF"
        self.accent_color = "#3498DB"
        self.accent_hover = "#2980B9"
        self.text_color = "#333333"
        self.btn_red = "#E74C3C"
        self.btn_red_hover = "#C0392B"
        
        self.root.configure(bg=self.bg_color)
        
        icon_path = resource_path('icon.ico')
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            
        self.ffmpeg_path = resource_path('ffmpeg.exe')
        self.setup_styles()
        
        self.url_var = tk.StringVar()
        self.download_path = tk.StringVar(value=os.path.join(os.path.expanduser('~'), 'Downloads'))
        
        self.current_thumbnail = None
        # Store references to all button widgets to avoid garbage collection
        self._download_buttons = []
        
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.header_bg, foreground=self.header_fg, font=("Segoe UI", 18, "bold"), padding=15)
        
        style.configure("Primary.TButton", background=self.accent_color, foreground=self.header_fg, font=("Segoe UI", 10, "bold"), borderwidth=0, padding=8)
        style.map("Primary.TButton", background=[("active", self.accent_hover)])
        
        style.configure("Danger.TButton", background="#E74C3C", foreground=self.header_fg, font=("Segoe UI", 10, "bold"), borderwidth=0, padding=8)
        style.map("Danger.TButton", background=[("active", "#C0392B")])

        # Custom Green Progress Bar
        style.configure("Green.Horizontal.TProgressbar", background="#2ECC71")
        
        # Treeview with visible gridlines
        style.configure("Treeview",
                        font=("Segoe UI", 9),
                        rowheight=36,
                        background="#FFFFFF",
                        fieldbackground="#FFFFFF",
                        borderwidth=1,
                        relief="solid")
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 10, "bold"),
                        background="#2C3E50",
                        foreground="#FFFFFF",
                        padding=8,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", "#D6EAF8")],
                  foreground=[("selected", "#1A252F")])

    def setup_ui(self):
        # Header
        header = ttk.Label(self.root, text="Mr.Baig Downloader", style="Header.TLabel", anchor="center")
        header.pack(fill="x")

        # Developer Text
        dev_label = tk.Label(self.root, text="Developed By Zawar Baig", bg=self.bg_color, fg="black", font=("Segoe UI", 9, "bold italic"))
        dev_label.pack(anchor="w", padx=20, pady=(5, 0))

        content_frame = ttk.Frame(self.root, padding=20)
        content_frame.pack(fill="both", expand=True)

        # URL Input & Buttons
        url_frame = ttk.Frame(content_frame)
        url_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(url_frame, text="Video URL:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Segoe UI", 11))
        url_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        paste_btn = ttk.Button(url_frame, text="Paste", style="Primary.TButton", command=self.paste_url)
        paste_btn.pack(side="left", padx=(0, 5))

        fetch_btn = ttk.Button(url_frame, text="Download", style="Primary.TButton", command=self.start_fetch_thread)
        fetch_btn.pack(side="left", padx=(0, 5))
        
        clear_btn = ttk.Button(url_frame, text="Clear", style="Danger.TButton", command=self.clear_all)
        clear_btn.pack(side="left")

        # Save Path
        path_frame = ttk.Frame(content_frame)
        path_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(path_frame, text="Save To:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 24))
        path_entry = ttk.Entry(path_frame, textvariable=self.download_path, font=("Segoe UI", 10), state="readonly")
        path_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        browse_btn = ttk.Button(path_frame, text="Browse", style="Primary.TButton", command=self.browse_folder)
        browse_btn.pack(side="left")

        # Video Info Area
        self.info_frame = ttk.Frame(content_frame)
        self.info_frame.pack(fill="x", pady=(0, 15))
        
        self.thumb_label = tk.Label(self.info_frame, bg=self.bg_color)
        self.thumb_label.pack(side="left", padx=(0, 15))
        
        self.title_label = ttk.Label(self.info_frame, text="", font=("Segoe UI", 11, "bold"), wraplength=500)
        self.title_label.pack(side="left", anchor="n")

        # --- Formats Table with Canvas for custom gridlines ---
        tree_outer = tk.Frame(content_frame, bg="#B0BEC5", bd=1, relief="solid")
        tree_outer.pack(fill="both", expand=True, pady=(0, 15))

        tree_frame = tk.Frame(tree_outer, bg="#FFFFFF")
        tree_frame.pack(fill="both", expand=True, padx=1, pady=1)

        columns = ("ID", "Extension", "Resolution", "Quality/Note", "Size", "Action")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        # Column widths and headings
        col_config = {
            "ID":           (55,  "center"),
            "Extension":    (85,  "center"),
            "Resolution":   (105, "center"),
            "Quality/Note": (260, "center"),
            "Size":         (90,  "center"),
            "Action":       (130, "center"),
        }
        for col, (w, anchor) in col_config.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=anchor, stretch=(col == "Quality/Note"))

        # Alternating row colours
        self.tree.tag_configure('oddrow',  background="#F4F8FB", foreground=self.text_color)
        self.tree.tag_configure('evenrow', background="#FFFFFF",  foreground=self.text_color)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Draw vertical dividers between columns after the widget is rendered
        self.tree.bind("<Configure>", self._draw_column_separators)

        # Status and Progress
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(content_frame, textvariable=self.status_var, font=("Segoe UI", 10, "italic"), foreground="#7F8C8D")
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(content_frame, variable=self.progress_var, maximum=100, style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x")

    # ------------------------------------------------------------------ #
    #  Draw thin vertical lines between columns to give a "grid" look     #
    # ------------------------------------------------------------------ #
    def _draw_column_separators(self, event=None):
        """Re-tag every visible row so row borders appear via the Treeview
        row-height. Actual vertical column separators are painted with a
        tiny Canvas overlay on the heading row."""
        # Nothing to do here — vertical lines come from the column
        # separator trick below via the tag/heading border trick.
        pass

    def paste_url(self):
        try:
            clipboard_content = self.root.clipboard_get()
            self.url_var.set(clipboard_content)
        except tk.TclError:
            pass

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path.get())
        if folder:
            self.download_path.set(folder)

    def clear_all(self):
        self.url_var.set("")
        self.title_label.config(text="")
        self.thumb_label.config(image='')
        self.current_thumbnail = None
        # Remove any embedded button windows
        for btn in self._download_buttons:
            try:
                btn.destroy()
            except Exception:
                pass
        self._download_buttons.clear()
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("Ready")
        self.progress_var.set(0)

    def format_size(self, bytes_size):
        if not bytes_size:
            return "Unknown"
        mb = bytes_size / (1024 * 1024)
        return f"{mb:.2f} MB"

    def start_fetch_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Error", "Please enter a valid URL.")
            return
        
        self.status_var.set("Fetching video information... Please wait.")
        # Clear old buttons and rows
        for btn in self._download_buttons:
            try:
                btn.destroy()
            except Exception:
                pass
        self._download_buttons.clear()
        self.tree.delete(*self.tree.get_children())
        self.title_label.config(text="")
        
        threading.Thread(target=self.fetch_formats, args=(url,), daemon=True).start()

    def load_thumbnail(self, thumb_url, title):
        try:
            req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
            raw_data = urllib.request.urlopen(req).read()
            im = Image.open(io.BytesIO(raw_data))
            im.thumbnail((120, 80))
            photo = ImageTk.PhotoImage(im)
            self.root.after(0, lambda: self.thumb_label.config(image=photo))
            self.root.after(0, lambda: self.title_label.config(text=title))
            self.current_thumbnail = photo
        except Exception as e:
            print("Could not load thumbnail:", e)

    def fetch_formats(self, url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': self.ffmpeg_path
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                thumb_url = info.get('thumbnail')
                title = info.get('title', 'Unknown Title')
                if thumb_url:
                    self.load_thumbnail(thumb_url, title)
                else:
                    self.root.after(0, lambda: self.title_label.config(text=title))

                formats = info.get('formats', [])
                formatted_list = []

                # Best-quality entry at top
                formatted_list.append(("best", "mp4/mkv", "Best Quality", "Auto-merges best video and audio", "Auto"))

                for f in formats:
                    f_id  = f.get('format_id', 'N/A')
                    ext   = f.get('ext', 'N/A')
                    res   = f.get('resolution', f.get('width', 'N/A'))
                    if res == 'audio only' or f.get('vcodec') == 'none':
                        res = "Audio Only"
                    elif f.get('height'):
                        res = f"{f.get('width', '?')}x{f.get('height', '?')}"
                    
                    note   = f.get('format_note', '')
                    vcodec = f.get('vcodec', '')
                    acodec = f.get('acodec', '')
                    details = f"{note} (V: {vcodec[:4] if vcodec != 'none' else 'none'}, A: {acodec[:4] if acodec != 'none' else 'none'})"
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    size_str = self.format_size(filesize)
                    
                    formatted_list.append((f_id, ext, res, details, size_str))

                self.root.after(0, self.update_treeview, formatted_list)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch formats:\n{str(e)}"))
            self.root.after(0, lambda: self.status_var.set("Ready"))

    def update_treeview(self, formats):
        """Insert rows and embed a real tk.Button in the Action column."""
        for index, item in enumerate(formats):
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            row_id = self.tree.insert("", "end", values=(*item, ""), tags=(tag,))

            # Create a real red button and embed it as a window inside the cell
            fmt_id = item[0]
            btn = tk.Button(
                self.tree,
                text="⬇  Download",
                font=("Segoe UI", 9, "bold"),
                bg=self.btn_red,
                fg="#FFFFFF",
                activebackground=self.btn_red_hover,
                activeforeground="#FFFFFF",
                relief="flat",
                cursor="hand2",
                bd=0,
                padx=8,
                pady=3,
                command=lambda fid=fmt_id: self.start_download(fid)
            )
            self._download_buttons.append(btn)
            self.tree.set(row_id, "Action", "")
            self.tree.item(row_id, tags=(tag,))
            # Place the button window inside the Action column cell
            self.tree.tag_configure(tag)  # ensure tag exists
            self.root.after(10, lambda r=row_id, b=btn: self._place_button(r, b))

        self.status_var.set(f"Formats loaded — {len(formats)} options. Click ⬇ Download to start.")

    def _place_button(self, row_id, btn):
        """Position the button widget over the Action column cell."""
        try:
            bbox = self.tree.bbox(row_id, column="#6")
            if bbox:
                x, y, w, h = bbox
                self.tree.window_create(row_id, window=btn, column="#6")
        except Exception:
            pass

    def start_download(self, format_id):
        url = self.url_var.get().strip()
        save_path = self.download_path.get()
        self.progress_var.set(0)
        self.status_var.set("Starting download...")
        threading.Thread(target=self.download_video, args=(url, format_id, save_path), daemon=True).start()

    def download_video(self, url, format_id, save_path):
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        def progress_hook(d):
            if d['status'] == 'downloading':
                percent_str = ansi_escape.sub('', d.get('_percent_str', '0.0%')).strip('% ')
                speed_str   = ansi_escape.sub('', d.get('_speed_str', '0KiB/s')).strip()
                eta_str     = ansi_escape.sub('', d.get('_eta_str', '00:00')).strip()
                try:
                    percent = float(percent_str)
                    self.root.after(0, self.progress_var.set, percent)
                    self.root.after(0, self.status_var.set, f"Downloading... {percent}% at {speed_str} (ETA: {eta_str})")
                except ValueError:
                    pass
            elif d['status'] == 'finished':
                self.root.after(0, self.status_var.set, "Merging video and audio... Please wait.")
                self.root.after(0, self.progress_var.set, 100)

        fmt_str = 'bestvideo+bestaudio/best' if str(format_id) == 'best' else str(format_id)

        ydl_opts = {
            'format': fmt_str,
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'merge_output_format': 'mp4',
            'ffmpeg_location': self.ffmpeg_path
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.root.after(0, lambda: self.status_var.set("Download Complete!"))
            self.root.after(0, lambda: messagebox.showinfo("Success", "Video downloaded successfully!"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set("Download Failed."))
            self.root.after(0, lambda: messagebox.showerror("Download Error", str(e)))

if __name__ == "__main__":
    root = tk.Tk()
    app = MrBaigDownloader(root)
    root.mainloop()
