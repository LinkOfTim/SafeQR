"""Tkinter-интерфейс для приложения SafeQR."""
from __future__ import annotations

import threading
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import BOTH, CENTER, END, LEFT, E, Button, Frame, Label, W, X, filedialog, messagebox, StringVar
from tkinter import ttk
from tkinter import scrolledtext
from typing import Optional

from PIL import Image, ImageTk

from safeqr import generator, scanner, security
from safeqr.utils import validators
from safeqr.utils.logger import get_log_path, log_error


class SafeQRApp(ttk.Frame):
    """Главное виджет-приложение, включающее все вкладки."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.master.title("SafeQR – генератор и сканер")
        self.master.geometry("900x600")
        self.master.minsize(800, 500)
        self.pack(fill=BOTH, expand=True)

        self.preview_path = Path(tempfile.gettempdir()) / "safeqr_preview.png"
        self.preview_image: Optional[ImageTk.PhotoImage] = None
        self.latest_payload: Optional[str] = None
        self.recent_checks: list[tuple[str, str]] = []

        self._build_ui()

    # --- построение вкладок ---
    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=BOTH, expand=True)

        self.tab_generate = Frame(notebook)
        self.tab_scan = Frame(notebook)
        self.tab_reports = Frame(notebook)

        notebook.add(self.tab_generate, text="Генерация QR")
        notebook.add(self.tab_scan, text="Сканирование QR")
        notebook.add(self.tab_reports, text="Отчёты")

        self._build_generator_tab()
        self._build_scan_tab()
        self._build_reports_tab()

    def _build_generator_tab(self) -> None:
        self.input_var = StringVar()
        entry = ttk.Entry(self.tab_generate, textvariable=self.input_var, width=80)
        entry.pack(padx=20, pady=10, fill=X)

        buttons_frame = Frame(self.tab_generate)
        buttons_frame.pack(fill=X, padx=20)

        Button(buttons_frame, text="Создать QR", command=self._handle_generate).pack(side=LEFT, padx=5)
        Button(buttons_frame, text="Сохранить в файл", command=self._handle_save).pack(side=LEFT, padx=5)

        self.preview_label = Label(self.tab_generate, text="Предпросмотр QR появится здесь", relief="sunken")
        self.preview_label.pack(fill=BOTH, expand=True, padx=20, pady=10)

    def _build_scan_tab(self) -> None:
        scan_buttons = Frame(self.tab_scan)
        scan_buttons.pack(fill=X, padx=20, pady=10)

        Button(scan_buttons, text="Сканировать из файла", command=self._scan_from_file).pack(side=LEFT, padx=5)
        Button(scan_buttons, text="Сканировать с камеры", command=self._scan_from_camera_async).pack(side=LEFT, padx=5)

        self.scan_result_var = StringVar(value="Результат: нет данных")
        ttk.Label(self.tab_scan, textvariable=self.scan_result_var, font=("Arial", 12, "bold")).pack(padx=20, pady=10, anchor=W)

        self.security_label = Label(self.tab_scan, text="Уровень риска: нет", bg="lightgrey", width=40)
        self.security_label.pack(padx=20, pady=5, anchor=W)

        self.security_report = scrolledtext.ScrolledText(self.tab_scan, height=10, state="disabled")
        self.security_report.pack(fill=BOTH, expand=True, padx=20, pady=10)

    def _build_reports_tab(self) -> None:
        log_frame = Frame(self.tab_reports)
        log_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        Button(log_frame, text="Обновить журнал", command=self._update_log_view).pack(anchor=E)
        self.log_view = scrolledtext.ScrolledText(log_frame, height=15, state="disabled")
        self.log_view.pack(fill=BOTH, expand=True, pady=5)

        ttk.Label(self.tab_reports, text="Последние проверенные ссылки").pack(anchor=W, padx=20, pady=5)
        self.links_table = ttk.Treeview(self.tab_reports, columns=("url", "risk"), show="headings", height=5)
        self.links_table.heading("url", text="Ссылка")
        self.links_table.heading("risk", text="Риск")
        self.links_table.column("url", width=600)
        self.links_table.column("risk", width=100, anchor=CENTER)
        self.links_table.pack(fill=BOTH, expand=True, padx=20, pady=5)

    # --- генерация ---
    def _handle_generate(self) -> None:
        data = self.input_var.get()
        try:
            result_path = generator.generate_qr(data, str(self.preview_path))
            self.latest_payload = data
            self._show_preview(result_path)
            messagebox.showinfo("Успех", f"QR-код создан: {result_path}")
        except Exception as exc:
            log_error("GUI_GENERATE", str(exc))
            messagebox.showerror("Ошибка", str(exc))

    def _show_preview(self, image_path: str) -> None:
        with Image.open(image_path) as image:
            image.thumbnail((350, 350))
            self.preview_image = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_image, text="")

    def _handle_save(self) -> None:
        if not self.latest_payload:
            messagebox.showwarning("Нет данных", "Сначала создайте QR-код.")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", ".png")])
        if not filename:
            return
        try:
            result = generator.generate_qr(self.latest_payload, filename)
            messagebox.showinfo("Сохранено", f"Файл сохранён: {result}")
        except Exception as exc:
            log_error("GUI_SAVE", str(exc))
            messagebox.showerror("Ошибка", str(exc))

    # --- сканирование ---
    def _scan_from_file(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("Изображения", ".png .jpg .jpeg .bmp")])
        if not file_path:
            return
        try:
            payload = scanner.scan_from_file(file_path)
            self._handle_scan_result(payload)
        except Exception as exc:
            log_error("GUI_SCAN_FILE", str(exc))
            messagebox.showerror("Ошибка", str(exc))

    def _scan_from_camera_async(self) -> None:
        messagebox.showinfo("Камера", "Запуск сканирования. Для отмены закройте окно камеры.")
        threading.Thread(target=self._scan_from_camera_worker, daemon=True).start()

    def _scan_from_camera_worker(self) -> None:
        try:
            payload = scanner.scan_from_camera()
        except Exception as exc:
            log_error("GUI_SCAN_CAMERA", str(exc))
            self.after(0, lambda: messagebox.showerror("Ошибка", str(exc)))
            return
        self.after(0, lambda: self._handle_scan_result(payload))

    def _handle_scan_result(self, payload: Optional[str]) -> None:
        if not payload:
            self.scan_result_var.set("QR-код не обнаружен")
            self.security_label.configure(text="Уровень риска: нет", bg="lightgrey")
            self._update_security_text([])
            return

        self.scan_result_var.set(f"Результат: {payload}")
        report = security.check_url_safety(payload)
        self._update_security_ui(report)
        self._remember_link(payload, report["risk_level"])

    def _update_security_ui(self, report: dict) -> None:
        risk = report["risk_level"]
        color = {"low": "#17a589", "medium": "#f4d03f", "high": "#e74c3c"}.get(risk, "lightgrey")
        text = f"Уровень риска: {risk.upper()}"
        self.security_label.configure(text=text, bg=color)
        self._update_security_text(report["warnings"])

    def _update_security_text(self, warnings: list[str]) -> None:
        self.security_report.configure(state="normal")
        self.security_report.delete("1.0", END)
        if not warnings:
            self.security_report.insert(END, "Предупреждений нет. Ссылка выглядит безопасной.")
        else:
            for item in warnings:
                self.security_report.insert(END, f"• {item}\n")
        self.security_report.configure(state="disabled")

    # --- отчёты ---
    def _update_log_view(self) -> None:
        log_path = get_log_path()
        content = "Файл журнала ещё не создан."
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
        self.log_view.configure(state="normal")
        self.log_view.delete("1.0", END)
        self.log_view.insert(END, content)
        self.log_view.configure(state="disabled")

    def _remember_link(self, url: str, risk: str) -> None:
        normalized = validators.normalize_url(url)
        self.recent_checks.append((normalized, risk))
        self.recent_checks = self.recent_checks[-10:]
        for row in self.links_table.get_children():
            self.links_table.delete(row)
        for link, risk_level in self.recent_checks:
            self.links_table.insert("", END, values=(link, risk_level.upper()))
        self._update_log_view()


def run_app() -> None:
    """Запускает графическое приложение."""
    root = tk.Tk()
    SafeQRApp(root)
    root.mainloop()
