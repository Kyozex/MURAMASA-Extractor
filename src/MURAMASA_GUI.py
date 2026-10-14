"""MURAMASA-Extractor Windows desktop interface."""

from __future__ import annotations

import json
import io
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from tkinter import Canvas, filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

import MURAMASA


APP_NAME = "MURAMASA-Extractor"
PROFILE_LABELS = {
    "自动识别": "auto",
    "本篇": "muramasa",
    "邪念编": "janen",
    "赎罪篇": "shokuzai",
}
ENCODING_LABELS = {
    "自动": None,
    "日文 CP932": "cp932",
    "中文 GBK": "gbk",
    "UTF-8": "utf-8",
}
PROFILE_NAMES = {"muramasa": "本篇", "janen": "邪念编", "shokuzai": "赎罪篇"}


COLORS = {
    "background": "#0A0809",
    "sidebar": "#100C0D",
    "surface": "#171213",
    "surface_alt": "#24191A",
    "border": "#422729",
    "text": "#F1E9DD",
    "muted": "#B2A49A",
    "subtle": "#7D6B67",
    "accent": "#B83232",
    "accent_hover": "#D54A3F",
    "gold": "#C4A56F",
    "gold_hover": "#C9A83C",
    "paper": "#E2D3B7",
    "accent_dim": "#2B1517",
    "danger_bg": "#3A2025",
    "danger_hover": "#522B32",
    "danger_text": "#F19BA0",
    "log_text": "#C6B9AC",
    "danger": "#D55D55",
    "success": "#A4AE91",
}


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    source_dir = Path(__file__).resolve().parent
    return source_dir.parent if source_dir.name == "src" else source_dir


def resource_path(name: str | Path) -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    return (Path(bundle_dir) if bundle_dir else app_directory()) / name


def muramasa_banner(source: Image.Image | None, size: tuple[int, int]) -> Image.Image:
    """Create a dark red Fuji banner from the game's local title-screen art."""
    width, height = max(1, size[0]), max(1, size[1])
    if source is None:
        return Image.new("RGB", (width, height), COLORS["background"])

    scale = max(width / source.width, height / source.height)
    resized = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, min(resized.height - height, round((resized.height - height) * .18)))
    banner = resized.crop((left, top, left + width, top + height)).convert("RGBA")
    banner = ImageEnhance.Brightness(banner).enhance(.68)
    overlay = Image.new("RGBA", (width, height), (5, 4, 5, 0))
    draw = ImageDraw.Draw(overlay)
    # Keep the title area dark for contrast while letting the red Fuji show
    # through at the far edge of the banner.
    for x in range(0, width, 8):
        fade = x / max(1, width - 1)
        alpha = round(168 - 92 * fade)
        draw.rectangle((x, 0, min(width, x + 7), height), fill=(5, 4, 5, alpha))
    banner.alpha_composite(overlay)
    ImageDraw.Draw(banner).line((0, height - 2, width, height - 2), fill=(167, 44, 40, 170), width=2)
    return banner.convert("RGB")


def settings_path() -> Path:
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home()
    return base / "MURAMASA-Extractor" / "settings.json"


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:,.1f} {unit}" if unit != "B" else f"{int(value):,} B"
        value /= 1024
    return f"{value:,.1f} TB"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}时 {minutes:02d}分"
    if minutes:
        return f"{minutes}分 {seconds:02d}秒"
    return f"{seconds}秒"


class ThemeDropdown(ctk.CTkFrame):
    """Theme-matched selector with a separate, precisely anchored popup."""

    _active_dropdown: "ThemeDropdown | None" = None
    def __init__(self, master, values: list[str], variable, command=None) -> None:
        super().__init__(master, height=38, corner_radius=0, fg_color="transparent")
        self.values = list(values)
        self.variable = variable
        self.command = command
        self.enabled = True
        self.expanded = False
        self.hovered = False
        self.highlighted_index = 0
        self._popup_hover_index: int | None = None
        self._popup_buttons: list[ctk.CTkButton] = []
        self._popup: ctk.CTkToplevel | None = None
        self._outside_click_id = None
        self._root_window = self.winfo_toplevel()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._control = ctk.CTkFrame(
            self, height=38, corner_radius=9, border_width=1,
            fg_color=COLORS["surface_alt"], border_color=COLORS["border"],
        )
        self._control.grid(row=0, column=0, sticky="ew")
        self._control.grid_columnconfigure(0, weight=1)
        self._control.grid_rowconfigure(0, weight=1)
        self._value_label = ctk.CTkLabel(
            self._control, text=self.variable.get(), anchor="w", fg_color="transparent",
            text_color=COLORS["text"], font=("Microsoft YaHei UI", 10),
        )
        # Keep the label inside the control's border. Stretching it vertically
        # to the full frame height paints over the top and bottom strokes,
        # which is especially visible when the focused border turns red.
        self._value_label.grid(row=0, column=0, sticky="ew", padx=(13, 4), pady=2)

        # A plain, familiar dropdown glyph keeps the control legible without
        # turning the arrow into a separate decorative element.
        self._arrow_label = ctk.CTkLabel(
            self._control, text="▾", width=30, fg_color="transparent",
            text_color=COLORS["muted"], font=("Segoe UI Symbol", 13), takefocus=1,
        )
        # Keep the arrow label's rounded canvas away from the right border.
        # CTkLabel paints its own rounded surface even with a transparent
        # foreground; a 2 px gap lets that corner visually interrupt the
        # parent's red outline on high-DPI Windows displays.
        self._arrow_label.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=2)
        self._focus_widget = self._arrow_label._label

        for widget in (self, self._control, self._value_label, self._arrow_label, self._focus_widget):
            widget.bind("<Button-1>", self._toggle, add="+")
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")
            widget.bind("<KeyPress>", self._on_key, add="+")
        self._trace_id = self.variable.trace_add("write", self._on_variable_changed)

    def _on_variable_changed(self, *_args) -> None:
        try:
            if self.winfo_exists():
                self._value_label.configure(text=self.variable.get())
                if self.expanded:
                    self._refresh_popup_buttons()
        except Exception:
            pass

    def _refresh_control(self) -> None:
        if not self.enabled:
            background, border, text, arrow = COLORS["surface"], COLORS["border"], COLORS["subtle"], COLORS["subtle"]
        elif self.expanded:
            background, border, text, arrow = COLORS["surface"], COLORS["accent"], COLORS["text"], COLORS["muted"]
        elif self.hovered:
            background, border, text, arrow = COLORS["surface_alt"], COLORS["accent"], COLORS["text"], COLORS["gold_hover"]
        else:
            background, border, text, arrow = COLORS["surface_alt"], COLORS["border"], COLORS["text"], COLORS["muted"]
        self._control.configure(fg_color=background, border_color=border)
        self._value_label.configure(text_color=text)
        self._arrow_label.configure(text_color=arrow)

    def _on_enter(self, _event=None) -> None:
        self.hovered = True
        self._refresh_control()

    def _on_leave(self, _event=None) -> None:
        self.hovered = False
        self._refresh_control()

    def _toggle(self, _event=None) -> str:
        if not self.enabled:
            return "break"
        self._focus_widget.focus_set()
        if self.expanded:
            self.close()
        else:
            self.open()
        return "break"

    def open(self) -> None:
        if not self.enabled or self.expanded or not self.values:
            return
        active = ThemeDropdown._active_dropdown
        if active is not None and active is not self:
            active.close()

        self.expanded = True
        self.highlighted_index = self._current_index()
        self._popup_hover_index = None
        self._refresh_control()

        ThemeDropdown._active_dropdown = self

        # Keep the menu in its own overrideredirect window. Putting these
        # buttons in the selector's grid makes the whole parent card reflow;
        # its opaque button backgrounds then sit directly over the card edge.
        popup = ctk.CTkToplevel(self._root_window)
        self._popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(self._root_window)
        popup.configure(fg_color=COLORS["background"])

        shell = ctk.CTkFrame(
            popup, fg_color=COLORS["surface"], corner_radius=9,
            border_width=1, border_color=COLORS["border"],
        )
        shell.pack(fill="both", expand=True)
        for index in range(len(self.values)):
            shell.grid_columnconfigure(index, weight=1, uniform="choice")

        self._popup_buttons = []
        for index, value in enumerate(self.values):
            button = ctk.CTkButton(
                shell, text=value, height=32, corner_radius=6,
                fg_color=COLORS["surface_alt"], hover_color=COLORS["accent_dim"],
                text_color=COLORS["muted"], border_width=1, border_color=COLORS["surface_alt"],
                font=("Microsoft YaHei UI", 9), command=lambda i=index: self._choose(i),
            )
            button.grid(row=0, column=index, sticky="ew", padx=(4, 2 if index < len(self.values) - 1 else 4), pady=4)
            button.bind("<Enter>", lambda _event, i=index: self._set_highlight(i), add="+")
            button.bind("<Leave>", lambda event, i=index: self._on_segment_leave(event, i), add="+")
            self._popup_buttons.append(button)

        self._refresh_popup_buttons()
        popup.bind("<Escape>", lambda _event: self.close(), add="+")

        # Anchor to the actual visible control, not the transparent wrapper or
        # its grid parent. Tk reports screen pixels, while CTkToplevel.geometry
        # accepts DPI-scaled window dimensions, so only width/height are scaled.
        popup.update_idletasks()
        self._control.update_idletasks()
        control_x = self._control.winfo_rootx()
        control_y = self._control.winfo_rooty()
        control_width = self._control.winfo_width()
        control_height = self._control.winfo_height()
        popup_height = max(1, popup.winfo_reqheight())
        screen_height = self.winfo_screenheight()
        y = control_y + control_height + 4
        if y + popup_height > screen_height - 8:
            y = max(0, control_y - popup_height - 4)
        geometry_width = popup._reverse_window_scaling(control_width)
        geometry_height = popup._reverse_window_scaling(popup_height)
        popup.geometry(f"{geometry_width}x{geometry_height}+{control_x}+{y}")
        popup.deiconify()
        popup.lift()

        self._outside_click_id = self._root_window.bind_all("<Button-1>", self._on_outside_click, add="+")

    def _current_index(self) -> int:
        try:
            return self.values.index(self.variable.get())
        except ValueError:
            return 0

    def _refresh_popup_buttons(self) -> None:
        if not self.expanded:
            return
        selected_index = self._current_index()
        for index, button in enumerate(self._popup_buttons):
            if index == selected_index:
                background, border, text, hover = COLORS["accent"], COLORS["accent"], "#FFFFFF", COLORS["accent_hover"]
            elif index == self._popup_hover_index:
                background, border, text, hover = COLORS["accent_dim"], COLORS["accent"], COLORS["text"], COLORS["border"]
            elif index == self.highlighted_index:
                background, border, text, hover = COLORS["surface_alt"], COLORS["border"], COLORS["text"], COLORS["accent_dim"]
            else:
                background, border, text, hover = COLORS["surface_alt"], COLORS["surface_alt"], COLORS["muted"], COLORS["accent_dim"]
            button.configure(fg_color=background, border_color=border, border_width=1,
                             text_color=text, hover_color=hover)

    def _set_highlight(self, index: int) -> None:
        self.highlighted_index = index
        self._popup_hover_index = index
        self._refresh_popup_buttons()

    def _on_segment_leave(self, event, old_index: int) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.after_idle(lambda: self._restore_segment_highlight(event.x_root, event.y_root, old_index))

    def _restore_segment_highlight(self, x_root: int, y_root: int, old_index: int) -> None:
        if not self.expanded:
            return
        try:
            target = self._root_window.winfo_containing(x_root, y_root)
            target_path = str(target) if target is not None else ""
            self._popup_hover_index = None
            for index, button in enumerate(self._popup_buttons):
                button_path = str(button)
                if target_path == button_path or target_path.startswith(button_path + "."):
                    self._popup_hover_index = index
                    self.highlighted_index = index
                    break
            else:
                if self.highlighted_index == old_index:
                    self.highlighted_index = self._current_index()
            self._refresh_popup_buttons()
        except Exception:
            pass

    def _choose(self, index: int) -> str:
        if not self.enabled or not 0 <= index < len(self.values):
            return "break"
        self.variable.set(self.values[index])
        self.close()
        if self.command is not None:
            self.command(self.values[index])
        self._focus_widget.focus_set()
        return "break"

    def _on_key(self, event) -> str | None:
        key = event.keysym
        if key in ("Down", "Up", "Left", "Right", "space", "Return"):
            if not self.expanded:
                self.open()
            elif key in ("Down", "Right"):
                self.highlighted_index = (self.highlighted_index + 1) % len(self.values)
                self._popup_hover_index = None
                self._refresh_popup_buttons()
            elif key in ("Up", "Left"):
                self.highlighted_index = (self.highlighted_index - 1) % len(self.values)
                self._popup_hover_index = None
                self._refresh_popup_buttons()
            elif key in ("Return", "space"):
                self._choose(self.highlighted_index)
            return "break"
        if key == "Escape" and self.expanded:
            self.close()
            return "break"
        return None

    def _on_outside_click(self, event) -> None:
        if not self.expanded:
            return
        target = str(event.widget)
        control_paths = (str(self), str(self._control))
        popup_path = str(self._popup) if self._popup is not None else ""
        if any(target == path or target.startswith(path + ".") for path in control_paths):
            return
        if popup_path and (target == popup_path or target.startswith(popup_path + ".")):
            return
        self.close()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self.close()
        self._refresh_control()

    def close(self) -> None:
        popup, self._popup = self._popup, None
        self.expanded = False
        self._popup_buttons = []
        self._popup_hover_index = None
        if self._outside_click_id is not None:
            try:
                self._root_window._unbind(("bind", "all", "<Button-1>"), self._outside_click_id)
            except Exception:
                pass
            self._outside_click_id = None
        if ThemeDropdown._active_dropdown is self:
            ThemeDropdown._active_dropdown = None
        if popup is not None:
            try:
                if popup.winfo_exists():
                    popup.destroy()
            except Exception:
                pass
        try:
            if self.winfo_exists():
                self._refresh_control()
        except Exception:
            pass

    def destroy(self) -> None:
        self.close()
        try:
            self.variable.trace_remove("write", self._trace_id)
        except Exception:
            pass
        super().destroy()


class MuramasaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1160x790")
        self.minsize(1020, 700)
        self._fullscreen = False
        self._windowed_geometry: str | None = None
        self._windowed_state = "normal"
        self.configure(fg_color=COLORS["background"])
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self._set_window_icon()
        self.theme_bg_source = None
        self.theme_logo_source = None
        try:
            with Image.open(resource_path(Path("assets") / "images" / "title_background.png")) as image:
                self.theme_bg_source = image.convert("RGB")
        except (OSError, ValueError):
            pass
        try:
            with Image.open(resource_path(Path("assets") / "images" / "logo.png")) as image:
                logo = image.convert("RGBA")
                bbox = logo.getchannel("A").getbbox()
                self.theme_logo_source = logo.crop(bbox) if bbox else logo
        except (OSError, ValueError):
            pass
        self.hero_photo = None
        self.hero_logo_photo = None
        self.hero_resize_job = None
        self.hero_last_size = (0, 0)

        self.events: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.archive_browser: ArchiveBrowser | None = None
        self.busy = False
        self.output_was_edited = False
        self.log_lines: list[str] = []
        self.started_at = 0.0
        self.last_progress = (0, 0, "", 0)

        saved = self._load_settings()
        self.archive_var = ctk.StringVar(value=saved.get("archive", ""))
        self.output_var = ctk.StringVar(value=saved.get("output", ""))
        saved_profile = saved.get("profile", "自动识别")
        saved_profile = {"本篇 · Muramasa": "本篇", "邪念编 · Janen Hen": "邪念编", "赎罪篇 · Shokuzai Hen": "赎罪篇"}.get(saved_profile, saved_profile)
        saved_encoding = saved.get("encoding", "自动")
        saved_encoding = {"自动（推荐）": "自动", "日文 · CP932": "日文 CP932",
                          "简体中文 · GBK": "中文 GBK", "Unicode · UTF-8": "UTF-8"}.get(saved_encoding, saved_encoding)
        self.profile_var = ctk.StringVar(value=saved_profile if saved_profile in PROFILE_LABELS else "自动识别")
        self.encoding_var = ctk.StringVar(value=saved_encoding if saved_encoding in ENCODING_LABELS else "自动")
        self.open_after_var = ctk.BooleanVar(value=saved.get("open_after", True))
        self.status_var = ctk.StringVar(value="就绪")
        self.profile_result_var = ctk.StringVar(value="尚未分析")
        self.count_result_var = ctk.StringVar(value="—")
        self.size_result_var = ctk.StringVar(value="—")
        self.progress_text_var = ctk.StringVar(value="等待开始")
        self.progress_detail_var = ctk.StringVar(value="")

        if self.archive_var.get() and not self.output_var.get():
            self.output_var.set(self._default_output(self.archive_var.get()))
        if not self.archive_var.get():
            self._find_default_archive()

        self._build_layout()
        self._refresh_profile_badge()
        self.bind("<F11>", self._toggle_fullscreen, add="+")
        self.bind("<Escape>", self._exit_fullscreen, add="+")
        self.after(100, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_icon(self) -> None:
        icon = resource_path(Path("assets") / "icons" / "muramasa.ico")
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

    def _load_settings(self) -> dict:
        try:
            return json.loads(settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}

    def _save_settings(self) -> None:
        target = settings_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "archive": self.archive_var.get().strip(),
                "output": self.output_var.get().strip(),
                "profile": self.profile_var.get(),
                "encoding": self.encoding_var.get(),
                "open_after": self.open_after_var.get(),
            }
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self._append_log(f"[提示] 无法保存设置：{exc}")

    def _find_default_archive(self) -> None:
        archive_dir = app_directory() / "npa"
        if archive_dir.is_dir():
            candidates = sorted(archive_dir.glob("*.npa"), key=lambda p: (p.name.lower() != "cg.npa", p.name.lower()))
            if candidates:
                self.archive_var.set(str(candidates[0]))
                self.output_var.set(self._default_output(str(candidates[0])))

    @staticmethod
    def _default_output(archive: str) -> str:
        path = Path(archive)
        return str(path.with_name(path.stem + "_解包"))

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.main.grid(row=0, column=0, sticky="nsew", padx=26, pady=20)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(4, weight=1)

        self._build_header()
        self._build_source_cards()
        self._build_options()
        self._build_progress_card()
        self._build_log_card()
        self._build_status()

    def _build_header(self) -> None:
        self.hero_canvas = Canvas(self.main, height=150, bg=COLORS["background"],
                                  highlightthickness=0, bd=0)
        self.hero_canvas.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        self.hero_canvas.bind("<Configure>", self._queue_hero_resize)
        self.after_idle(lambda: self._set_hero_background(
            self.hero_canvas.winfo_width(), self.hero_canvas.winfo_height()))

    def _queue_hero_resize(self, event) -> None:
        width, height = max(1, event.width), max(1, event.height)
        if (width, height) == self.hero_last_size:
            return
        if self.hero_resize_job is not None:
            try:
                self.after_cancel(self.hero_resize_job)
            except Exception:
                pass
        self.hero_resize_job = self.after(90, lambda: self._set_hero_background(width, height))

    def _set_hero_background(self, width: int, height: int) -> None:
        if not hasattr(self, "hero_canvas") or not self.hero_canvas.winfo_exists():
            return
        size = (max(1, width), max(1, height))
        if size == self.hero_last_size and self.hero_photo is not None:
            return
        banner = muramasa_banner(self.theme_bg_source, size)
        old_banner, old_logo = self.hero_photo, self.hero_logo_photo
        self.hero_canvas.delete("all")
        photo = ImageTk.PhotoImage(banner, master=self.hero_canvas)
        self.hero_canvas.create_image(0, 0, image=photo, anchor="nw")

        self.hero_canvas.create_text(34, 18, text="NPA EXTRACTOR",
                                     fill=COLORS["gold"], anchor="nw",
                                     font=("Segoe UI", 9, "bold"))
        self.hero_canvas.create_text(31, 44, text="装甲悪鬼村正",
                                     fill=COLORS["text"], anchor="nw",
                                     font=("Yu Mincho", 34, "bold"))
        self.hero_canvas.create_line(34, 101, 94, 101, fill=COLORS["accent"], width=3)
        self.hero_canvas.create_text(34, 113, text="十字羽製造",
                                     fill=COLORS["muted"], anchor="nw",
                                     font=("Microsoft YaHei UI", 10))

        logo_photo = None
        if self.theme_logo_source is not None:
            logo = self.theme_logo_source.copy()
            logo.thumbnail((min(140, max(1, width // 5)), max(1, height - 14)), Image.Resampling.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo, master=self.hero_canvas)
            self.hero_canvas.create_image(width - 24, height // 2, image=logo_photo, anchor="e")

        self.hero_photo = photo
        self.hero_logo_photo = logo_photo
        self.hero_last_size = size
        self.hero_resize_job = None

    def _card(self, parent, **kwargs):
        return ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=16,
                            border_width=1, border_color=COLORS["border"], **kwargs)

    @staticmethod
    def _bind_gold_text_hover(button: ctk.CTkButton) -> None:
        button.bind("<Enter>", lambda _event: button.configure(text_color=COLORS["gold_hover"]), add="+")
        button.bind("<Leave>", lambda _event: button.configure(text_color=COLORS["accent"]), add="+")

    def _build_source_cards(self) -> None:
        grid = ctk.CTkFrame(self.main, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        grid.grid_columnconfigure((0, 1), weight=1, uniform="source")

        archive = self._card(grid)
        archive.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        archive.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(archive, text="输入存档", font=("Microsoft YaHei UI", 12, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=17, pady=(14, 7))
        self.archive_entry = ctk.CTkEntry(archive, textvariable=self.archive_var, height=37, corner_radius=10,
                                          fg_color=COLORS["background"], border_color=COLORS["border"],
                                          text_color=COLORS["text"], placeholder_text="选择 NPA 文件…",
                                          font=("Segoe UI", 10))
        self.archive_entry.grid(row=1, column=0, sticky="ew", padx=(17, 8), pady=(0, 12))
        self.archive_entry.bind("<FocusOut>", lambda _event: self._archive_path_changed())
        self.archive_entry.bind("<Return>", lambda _event: self._archive_path_changed())
        ctk.CTkButton(archive, text="浏览", width=72, height=37, corner_radius=10, command=self._browse_archive,
                      fg_color=COLORS["surface_alt"], hover_color=COLORS["border"], text_color=COLORS["text"],
                      font=("Microsoft YaHei UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=(0, 17), pady=(0, 12))
        self.profile_badge = ctk.CTkLabel(archive, textvariable=self.profile_result_var, font=("Microsoft YaHei UI", 9), text_color=COLORS["muted"])
        self.profile_badge.grid(row=2, column=0, sticky="w", padx=17, pady=(0, 13))
        self.browse_contents_button = ctk.CTkButton(archive, text="浏览目录", width=88, height=26, corner_radius=8, command=self._browse_contents_clicked,
                      fg_color="transparent", hover_color=COLORS["surface_alt"], text_color=COLORS["accent"],
                      font=("Microsoft YaHei UI", 9, "bold"))
        self.browse_contents_button.grid(row=2, column=1, sticky="e", padx=12, pady=(0, 10))
        self._bind_gold_text_hover(self.browse_contents_button)

        output = self._card(grid)
        output.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        output.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(output, text="输出目录", font=("Microsoft YaHei UI", 12, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=17, pady=(14, 7))
        self.output_entry = ctk.CTkEntry(output, textvariable=self.output_var, height=37, corner_radius=10,
                                         fg_color=COLORS["background"], border_color=COLORS["border"],
                                         text_color=COLORS["text"], placeholder_text="选择解包文件夹…",
                                         font=("Segoe UI", 10))
        self.output_entry.grid(row=1, column=0, sticky="ew", padx=(17, 8), pady=(0, 12))
        self.output_entry.bind("<FocusOut>", lambda _event: setattr(self, "output_was_edited", True))
        ctk.CTkButton(output, text="浏览", width=72, height=37, corner_radius=10, command=self._browse_output,
                      fg_color=COLORS["surface_alt"], hover_color=COLORS["border"], text_color=COLORS["text"],
                      font=("Microsoft YaHei UI", 10, "bold")).grid(row=1, column=1, sticky="e", padx=(0, 17), pady=(0, 12))
        self.output_info_label = ctk.CTkLabel(output, text="", font=("Microsoft YaHei UI", 9), text_color=COLORS["muted"])
        self.output_info_label.grid(row=2, column=0, sticky="w", padx=17, pady=(0, 13))
        self.open_output_button = ctk.CTkButton(output, text="打开目录", width=88, height=26, corner_radius=8, command=self._open_output,
                      fg_color="transparent", hover_color=COLORS["surface_alt"], text_color=COLORS["accent"],
                      font=("Microsoft YaHei UI", 9, "bold"))
        self.open_output_button.grid(row=2, column=1, sticky="e", padx=12, pady=(0, 10))
        self._bind_gold_text_hover(self.open_output_button)

    def _build_options(self) -> None:
        card = self._card(self.main)
        card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="解包选项", font=("Microsoft YaHei UI", 11, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 7))

        options = ctk.CTkFrame(card, fg_color="transparent")
        options.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 12))
        options.grid_columnconfigure((0, 1), weight=1, uniform="selector")

        profile_group = ctk.CTkFrame(options, fg_color="transparent")
        profile_group.grid(row=0, column=0, sticky="ew", padx=(0, 18))
        profile_group.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(profile_group, text="游戏版本", font=("Microsoft YaHei UI", 9),
                     text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.profile_menu = ThemeDropdown(
            profile_group, values=list(PROFILE_LABELS), variable=self.profile_var,
            command=lambda _value: self._refresh_profile_badge(),
        )
        self.profile_menu.grid(row=1, column=0, sticky="ew")

        encoding_group = ctk.CTkFrame(options, fg_color="transparent")
        encoding_group.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        encoding_group.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(encoding_group, text="文件名编码", font=("Microsoft YaHei UI", 9),
                     text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.encoding_menu = ThemeDropdown(
            encoding_group, values=list(ENCODING_LABELS), variable=self.encoding_var,
        )
        self.encoding_menu.grid(row=1, column=0, sticky="ew")

        open_after_group = ctk.CTkFrame(options, fg_color="transparent")
        open_after_group.grid(row=0, column=2, sticky="ew", padx=(14, 2))
        open_after_group.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(open_after_group, text=" ", font=("Microsoft YaHei UI", 9),
                     text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.open_after_checkbox = ctk.CTkCheckBox(open_after_group, text="完成后打开文件夹", variable=self.open_after_var,
                                                   checkbox_width=17, checkbox_height=17, corner_radius=5,
                                                   fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                                                   checkmark_color=COLORS["background"], text_color=COLORS["muted"],
                                                   font=("Microsoft YaHei UI", 9))
        self.open_after_checkbox.grid(row=1, column=0, sticky="e")

    def _build_progress_card(self) -> None:
        card = self._card(self.main)
        card.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=17, pady=(14, 8))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, textvariable=self.progress_text_var, font=("Microsoft YaHei UI", 11, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        self.count_label = ctk.CTkLabel(top, textvariable=self.count_result_var, font=("Segoe UI", 9, "bold"), text_color=COLORS["accent"])
        self.count_label.grid(row=0, column=1, sticky="e", padx=(0, 14))
        self.size_label = ctk.CTkLabel(top, textvariable=self.size_result_var, font=("Segoe UI", 9), text_color=COLORS["muted"])
        self.size_label.grid(row=0, column=2, sticky="e")
        self.progress_bar = ctk.CTkProgressBar(card, height=8, corner_radius=8, fg_color=COLORS["surface_alt"], progress_color=COLORS["accent"])
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=17, pady=(0, 8))
        self.progress_bar.set(0)
        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=17, pady=(0, 13))
        bottom.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bottom, textvariable=self.progress_detail_var, font=("Microsoft YaHei UI", 9), text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="ew")
        self.cancel_button = ctk.CTkButton(bottom, text="取消任务", width=88, height=28, corner_radius=8,
                                           command=self._cancel, fg_color=COLORS["danger_bg"],
                                           hover_color=COLORS["danger_hover"], text_color=COLORS["danger_text"],
                                           font=("Microsoft YaHei UI", 9, "bold"), state="disabled")
        self.cancel_button.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.start_button = ctk.CTkButton(bottom, text="开始解包  →", width=130, height=34, corner_radius=10,
                                          command=self._extract_clicked, fg_color=COLORS["accent"],
                                          hover_color=COLORS["accent_hover"], text_color="#FFFFFF",
                                          font=("Microsoft YaHei UI", 10, "bold"))
        self.start_button.grid(row=0, column=2, sticky="e", padx=(9, 0))

    def _build_log_card(self) -> None:
        card = self._card(self.main)
        card.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(11, 5))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="运行日志", font=("Microsoft YaHei UI", 10, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text="保存日志", width=68, height=25, corner_radius=7, command=self._save_log,
                      fg_color="transparent", hover_color=COLORS["surface_alt"], text_color=COLORS["muted"],
                      font=("Microsoft YaHei UI", 8, "bold")).grid(row=0, column=1, padx=(0, 5))
        ctk.CTkButton(header, text="清空", width=48, height=25, corner_radius=7, command=self._clear_log,
                      fg_color="transparent", hover_color=COLORS["surface_alt"], text_color=COLORS["muted"],
                      font=("Microsoft YaHei UI", 8, "bold")).grid(row=0, column=2)
        self.log_box = ctk.CTkTextbox(card, corner_radius=10, fg_color=COLORS["background"],
                                      border_width=1, border_color=COLORS["border"],
                                      text_color=COLORS["log_text"],
                                      scrollbar_button_color=COLORS["surface_alt"],
                                      scrollbar_button_hover_color=COLORS["accent"],
                                      font=("Cascadia Mono", 9),
                                      wrap="none", activate_scrollbars=True)
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=13, pady=(0, 13))
        self.log_box.insert("end", "选择存档后，可浏览目录、预览图片或直接解包。\n")
        self.log_box.configure(state="disabled")

    def _build_status(self) -> None:
        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.grid(row=5, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bar, text="●", font=("Segoe UI", 9), text_color=COLORS["success"]).grid(row=0, column=0, sticky="w", padx=(2, 7))
        ctk.CTkLabel(bar, textvariable=self.status_var, font=("Microsoft YaHei UI", 9), text_color=COLORS["muted"], anchor="w").grid(row=0, column=1, sticky="ew")
        self.fullscreen_button = ctk.CTkButton(
            bar, text="全屏  F11", width=82, height=25, corner_radius=7,
            command=self._toggle_fullscreen, fg_color="transparent",
            hover_color=COLORS["surface_alt"], text_color=COLORS["muted"],
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        self.fullscreen_button.grid(row=0, column=2, padx=(10, 12))

    def _toggle_fullscreen(self, _event=None):
        if self._fullscreen:
            self.overrideredirect(False)
            self.update_idletasks()
            if self._windowed_state == "zoomed":
                self.state("zoomed")
            else:
                self.state("normal")
                if self._windowed_geometry:
                    self.geometry(self._windowed_geometry)
            self._fullscreen = False
            self.fullscreen_button.configure(text="全屏  F11")
        else:
            self._windowed_geometry = self.geometry()
            try:
                self._windowed_state = self.state()
            except Exception:
                self._windowed_state = "normal"
            if self._windowed_state == "zoomed":
                self.state("normal")
            # Tk's -fullscreen size is in unscaled screen units, while
            # CustomTkinter's window geometry applies its DPI scale. Use a
            # borderless window plus CTk geometry so the client area fills the
            # actual display and the grid gets the matching resize event.
            self.overrideredirect(True)
            self.update_idletasks()
            self.geometry(
                f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0"
            )
            self._fullscreen = True
            self.fullscreen_button.configure(text="退出全屏  Esc")
        return "break"

    def _exit_fullscreen(self, _event=None):
        if self._fullscreen:
            return self._toggle_fullscreen()

    def _refresh_profile_badge(self) -> None:
        self.profile_result_var.set(f"版本：{self.profile_var.get()}" if self.profile_var.get() != "自动识别" else "版本：自动识别")

    def _archive_path_changed(self) -> None:
        archive = self.archive_var.get().strip().strip('"')
        self.archive_var.set(archive)
        if archive and not self.output_was_edited:
            self.output_var.set(self._default_output(archive))
        self._reset_analysis()

    def _browse_archive(self) -> None:
        initial = self.archive_var.get().strip()
        initial_dir = str(Path(initial).parent) if initial else str(app_directory() / "npa")
        path = filedialog.askopenfilename(title="选择 NPA 存档", initialdir=initial_dir,
                                          filetypes=[("NPA 存档", "*.npa"), ("所有文件", "*.*")])
        if path:
            self.archive_var.set(path)
            self.output_was_edited = False
            self.output_var.set(self._default_output(path))
            self._reset_analysis()

    def _browse_output(self) -> None:
        initial = self.output_var.get().strip()
        initial_dir = initial if os.path.isdir(initial) else str(Path(initial).parent) if initial else str(app_directory())
        path = filedialog.askdirectory(title="选择解包输出文件夹", initialdir=initial_dir, mustexist=False)
        if path:
            self.output_var.set(path)
            self.output_was_edited = True

    def _reset_analysis(self) -> None:
        self.profile_result_var.set("版本：待识别")
        self.count_result_var.set("—")
        self.size_result_var.set("—")
        self.progress_bar.set(0)
        self.progress_text_var.set("等待开始")
        self.progress_detail_var.set("")

    def _get_profile(self) -> str:
        return PROFILE_LABELS.get(self.profile_var.get(), "auto")

    def _browse_contents_clicked(self) -> None:
        archive = self.archive_var.get().strip().strip('"')
        if not os.path.isfile(archive):
            messagebox.showerror("找不到存档", "请选择一个有效的 .npa 文件。", parent=self)
            return
        if self.busy:
            return
        if self.archive_browser is not None and self.archive_browser.winfo_exists():
            self.archive_browser.lift()
            self.archive_browser.focus_force()
            return
        self.archive_browser = ArchiveBrowser(self, archive, self._get_profile(),
                                              ENCODING_LABELS.get(self.encoding_var.get()))

    def _extract_clicked(self, selected_paths=None, selection_source=None) -> None:
        archive = self.archive_var.get().strip().strip('"')
        output = self.output_var.get().strip().strip('"')
        dialog_parent = selection_source or self
        if not os.path.isfile(archive):
            messagebox.showerror("找不到存档", "请选择有效的 NPA 文件。", parent=dialog_parent)
            return
        if not output:
            messagebox.showerror("缺少输出位置", "请选择输出目录。", parent=dialog_parent)
            return
        if os.path.isdir(output) and any(Path(output).iterdir()):
            description = "选中的同名文件会被覆盖。继续？" if selected_paths is not None else "目录中已有文件，同名文件会被覆盖。继续？"
            if not messagebox.askyesno("输出目录不为空", description, parent=dialog_parent):
                return

        try:
            Path(output).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("无法创建输出目录", str(exc), parent=dialog_parent)
            return

        self.cancel_event.clear()
        self.last_progress = (0, 0, "", 0)
        self.progress_bar.set(0)
        self._set_busy(True, mode="extract")
        self.status_var.set("正在解包…")
        self.progress_text_var.set("正在准备解包")
        self.progress_detail_var.set("正在读取存档目录")
        self.started_at = time.monotonic()
        self._append_log(f"[开始] 存档：{archive}")
        self._append_log(f"[开始] 输出：{output}")
        self._save_settings()
        self.worker = threading.Thread(target=self._extract_worker,
                                       args=(archive, output, self._get_profile(), ENCODING_LABELS.get(self.encoding_var.get()), selected_paths),
                                       daemon=True)
        self.worker.start()

    def _extract_selected(self, paths, source=None) -> None:
        if not paths:
            messagebox.showinfo("未选择文件", "请先选择文件。", parent=source or self)
            return
        self._extract_clicked(selected_paths=set(paths), selection_source=source)

    def _extract_worker(self, archive: str, output: str, profile: str, encoding: str | None,
                        selected_paths=None) -> None:
        try:
            MURAMASA.unpack(
                archive,
                output,
                crypto_profile=profile,
                file_path_encoding=encoding,
                progress_callback=lambda done, total, path, count: self.events.put(("progress", done, total, path, count)),
                cancel_callback=self.cancel_event.is_set,
                log_callback=lambda line: self.events.put(("log", line)),
                selected_paths=selected_paths,
            )
            self.events.put(("extract_done",))
        except InterruptedError:
            self.events.put(("cancelled",))
        except Exception as exc:
            self.events.put(("error", str(exc), traceback.format_exc()))

    def _cancel(self) -> None:
        if self.busy:
            self.cancel_event.set()
            self.cancel_button.configure(state="disabled", text="正在停止…")
            self.status_var.set("正在停止任务，请稍候…")
            self._append_log("[提示] 已请求取消，当前文件处理完成后将停止。")

    def _set_busy(self, busy: bool, mode: str = "") -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.start_button.configure(state=state, text="解包中…" if busy and mode == "extract" else "开始解包  →")
        self.archive_entry.configure(state=state)
        self.output_entry.configure(state=state)
        self.browse_contents_button.configure(state=state)
        self.profile_menu.set_enabled(not busy)
        self.encoding_menu.set_enabled(not busy)
        self.open_after_checkbox.configure(state=state)
        self.cancel_button.configure(state="normal" if busy and mode == "extract" else "disabled", text="取消任务")
        if self.archive_browser is not None and self.archive_browser.winfo_exists():
            self.archive_browser.set_extract_busy(busy)

    def _drain_events(self) -> None:
        # Keep each UI tick short. A large archive can enqueue thousands of
        # log/progress events; draining the entire queue here prevents Tk from
        # painting until extraction has nearly finished.
        pending_logs: list[str] = []
        latest_progress = None
        event_count = 0
        deadline = time.perf_counter() + 0.012

        def flush_pending() -> None:
            nonlocal latest_progress
            if pending_logs:
                self._append_logs(pending_logs)
                pending_logs.clear()
            if latest_progress is not None:
                self._update_progress(*latest_progress)
                latest_progress = None

        while event_count < 250 and time.perf_counter() < deadline:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            event_count += 1
            kind = event[0]
            if kind == "log":
                pending_logs.append(self._shorten_log(event[1]))
            elif kind == "progress":
                latest_progress = event[1:]
            else:
                # Preserve event order around completion, cancellation, and
                # errors by applying all earlier log/progress updates first.
                flush_pending()
                if kind == "extract_done":
                    self._extraction_complete()
                elif kind == "cancelled":
                    self._set_busy(False)
                    self.progress_text_var.set("已取消")
                    self.status_var.set("任务已取消 · 已写出的文件保留在输出文件夹中")
                    self._append_log("[完成] 任务已取消，已写出的文件保留在输出目录。")
                elif kind == "error":
                    self._set_busy(False)
                    self.progress_text_var.set("操作失败")
                    self.progress_detail_var.set(event[1])
                    self.status_var.set("操作失败")
                    self._append_logs([f"[错误] {event[1]}", event[2]])
                    messagebox.showerror("操作失败", event[1], parent=self)

        flush_pending()
        self.after(25, self._drain_events)

    def _shorten_log(self, message: str) -> str:
        if message.startswith("[write] "):
            output = self.output_var.get().strip()
            try:
                path = Path(message[8:])
                return "[写入] " + str(path.relative_to(output))
            except (ValueError, OSError):
                return "[写入] " + message[8:]
        if message.startswith("[log] data cipher:"):
            cipher = message.split(":", 1)[1].strip()
            short_name = {"MURAMASA": "本篇", "Janen Hen": "邪念编", "Shokuzai Hen": "赎罪篇"}.get(cipher, cipher)
            return "[加密] " + short_name
        if message.startswith("[log] unpack"):
            return "[完成] " + message
        return message

    def _update_progress(self, done: int, total: int, path: str, extracted: int) -> None:
        self.last_progress = (done, total, path, extracted)
        ratio = done / total if total else 0
        self.progress_bar.set(ratio)
        percent = ratio * 100
        self.progress_text_var.set(f"正在解包  ·  {percent:.1f}%")
        elapsed = time.monotonic() - self.started_at
        rate = done / elapsed if elapsed > .05 else 0
        remaining = (total - done) / rate if rate > 0 else 0
        suffix = f"预计剩余 {format_duration(remaining)}" if done < total else "即将完成"
        self.progress_detail_var.set(f"{done:,} / {total:,} 项 · 已写 {extracted:,} 个文件 · {suffix} · {path}")
        self.count_result_var.set(f"{extracted:,} 个文件")

    def _extraction_complete(self) -> None:
        self._set_busy(False)
        done, total, _path, extracted = self.last_progress
        elapsed = time.monotonic() - self.started_at
        self.progress_bar.set(1)
        self.progress_text_var.set("解包完成  ·  100%")
        self.progress_detail_var.set(f"成功写入 {extracted:,} 个文件  ·  用时 {format_duration(elapsed)}")
        self.count_result_var.set(f"{extracted:,} 个文件")
        self.size_result_var.set("完成")
        self.status_var.set(f"解包完成 · {extracted:,} 个文件已写入")
        self._append_log(f"[完成] {extracted:,} 个文件 · {format_duration(elapsed)}")
        self._save_settings()
        if self.open_after_var.get():
            self._open_output()

    def _open_output(self) -> None:
        output = self.output_var.get().strip().strip('"')
        if not output:
            return
        try:
            Path(output).mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(output)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", output])
            else:
                subprocess.Popen(["xdg-open", output])
        except OSError as exc:
            messagebox.showerror("无法打开文件夹", str(exc), parent=self)

    def _append_log(self, line: str) -> None:
        self._append_logs([line])

    def _append_logs(self, lines: list[str]) -> None:
        if not lines:
            return
        clean_lines = [line.rstrip("\r\n") for line in lines]
        self.log_lines.extend(clean_lines)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", "\n".join(clean_lines) + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_lines.clear()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _save_log(self) -> None:
        path = filedialog.asksaveasfilename(title="保存运行日志", defaultextension=".txt",
                                            initialfile="MURAMASA_解包日志.txt",
                                            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            Path(path).write_text("\n".join(self.log_lines) + "\n", encoding="utf-8-sig")
            self.status_var.set(f"日志已保存：{path}")
        except OSError as exc:
            messagebox.showerror("保存日志失败", str(exc), parent=self)

    def _on_close(self) -> None:
        if self.busy:
            if not messagebox.askyesno("任务仍在运行", "解包任务正在运行。现在退出会中断当前任务，确定退出吗？", parent=self):
                return
            self.cancel_event.set()
        self._save_settings()
        self.destroy()


class ArchiveBrowser(ctk.CTkToplevel):
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

    def __init__(self, app: MuramasaApp, archive_path: str, profile: str, encoding: str | None) -> None:
        super().__init__(app)
        self.app = app
        self.archive_path = archive_path
        self.requested_profile = profile
        self.encoding = encoding
        self.info: dict | None = None
        self.entries: list[dict] = []
        self.events: queue.Queue = queue.Queue()
        self.folder_iids: dict[str, str] = {}
        self.tree_items: dict[str, dict] = {}
        self.file_iids: dict[int, str] = {}
        self.visible_file_iids: list[str] = []
        self.selected_paths: list[str] = []
        self.preview_token = 0
        self.preview_ctk_image = None
        self.banner_photo = None
        self.banner_resize_job = None
        self.banner_last_size = (0, 0)
        self.header_info_text = ""

        self.title("存档内容")
        self.geometry("1060x680")
        self.minsize(900, 570)
        self.configure(fg_color=COLORS["background"])
        icon = resource_path(Path("assets") / "icons" / "muramasa.ico")
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass
        self.transient(app)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_window()
        self._set_status("正在读取目录…")
        threading.Thread(target=self._load_worker, daemon=True).start()
        self.after(100, self._poll_events)

    def _build_window(self) -> None:
        self.banner_canvas = Canvas(self, height=84, bg=COLORS["background"],
                                    highlightthickness=0, bd=0)
        self.banner_canvas.grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 12))
        self.banner_canvas.bind("<Configure>", self._queue_banner_resize)
        self.after_idle(lambda: self._set_banner_background(
            self.banner_canvas.winfo_width(), self.banner_canvas.winfo_height()))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 12))
        body.grid_columnconfigure(0, weight=6, uniform="browser")
        body.grid_columnconfigure(1, weight=5, uniform="browser")
        body.grid_rowconfigure(0, weight=1)

        browser = ctk.CTkFrame(body, fg_color=COLORS["surface"], corner_radius=15,
                                border_width=1, border_color=COLORS["border"])
        browser.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        browser.grid_columnconfigure(0, weight=1)
        browser.grid_rowconfigure(1, weight=1)
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(browser, textvariable=self.search_var, height=35, corner_radius=9,
                                         fg_color=COLORS["background"], border_color=COLORS["border"],
                                         text_color=COLORS["text"], placeholder_text="搜索文件或目录…",
                                         font=("Microsoft YaHei UI", 10))
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=13, pady=(13, 9))
        self.search_entry.bind("<KeyRelease>", self._search_changed)

        tree_frame = ctk.CTkFrame(browser, fg_color=COLORS["background"], corner_radius=10)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=13, pady=(0, 8))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("NPA.Treeview", background=COLORS["background"], foreground=COLORS["text"],
                        fieldbackground=COLORS["background"], rowheight=27, borderwidth=0,
                        font=("Microsoft YaHei UI", 9))
        style.map("NPA.Treeview", background=[("selected", COLORS["accent"])],
                  foreground=[("selected", COLORS["text"])])
        style.configure("NPA.Treeview.Heading", background=COLORS["surface_alt"],
                        foreground=COLORS["muted"], relief="flat",
                        font=("Microsoft YaHei UI", 9, "bold"))
        style.map("NPA.Treeview.Heading", background=[("active", COLORS["surface_alt"])])
        self.tree = ttk.Treeview(tree_frame, columns=("size", "kind"), show="tree headings",
                                 selectmode="extended", style="NPA.Treeview")
        self.tree.heading("#0", text="名称", anchor="w")
        self.tree.heading("size", text="大小", anchor="e")
        self.tree.heading("kind", text="类型", anchor="center")
        self.tree.column("#0", width=390, minwidth=190, stretch=True)
        self.tree.column("size", width=94, minwidth=82, stretch=False, anchor="e")
        self.tree.column("kind", width=70, minwidth=62, stretch=False, anchor="center")
        yscroll = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.tree.yview,
                                   width=12, corner_radius=6, fg_color=COLORS["background"],
                                   button_color=COLORS["accent"],
                                   button_hover_color=COLORS["gold_hover"])
        xscroll = ctk.CTkScrollbar(tree_frame, orientation="horizontal", command=self.tree.xview,
                                   height=12, corner_radius=6, fg_color=COLORS["background"],
                                   button_color=COLORS["accent"],
                                   button_hover_color=COLORS["gold_hover"])
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)

        controls = ctk.CTkFrame(browser, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=13, pady=(0, 12))
        controls.grid_columnconfigure(2, weight=1)
        self.selection_var = ctk.StringVar(value="已选 0 个文件")
        ctk.CTkButton(controls, text="全选", width=54, height=28, corner_radius=8,
                      command=self._select_all_visible, fg_color=COLORS["surface_alt"],
                      hover_color=COLORS["border"], text_color=COLORS["text"],
                      font=("Microsoft YaHei UI", 9)).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(controls, text="清除", width=54, height=28, corner_radius=8,
                      command=lambda: self.tree.selection_remove(self.tree.selection()),
                      fg_color=COLORS["surface_alt"], hover_color=COLORS["border"],
                      text_color=COLORS["text"], font=("Microsoft YaHei UI", 9)).grid(row=0, column=1)
        ctk.CTkLabel(controls, textvariable=self.selection_var, font=("Microsoft YaHei UI", 9),
                     text_color=COLORS["muted"]).grid(row=0, column=2, sticky="e", padx=8)
        self.extract_selected_button = ctk.CTkButton(controls, text="解包选中", width=100, height=32,
                                                     corner_radius=9, command=self._extract_selected,
                                                     fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                                                     text_color="#FFFFFF",
                                                     font=("Microsoft YaHei UI", 9, "bold"), state="disabled")
        self.extract_selected_button.grid(row=0, column=3, sticky="e")

        preview = ctk.CTkFrame(body, fg_color=COLORS["surface"], corner_radius=15,
                               border_width=1, border_color=COLORS["border"])
        preview.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        preview.grid_columnconfigure(0, weight=1)
        preview.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(preview, text="图片预览", font=("Microsoft YaHei UI", 12, "bold"),
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=16, pady=(15, 9))
        self.image_box = ctk.CTkFrame(preview, fg_color=COLORS["background"], corner_radius=11,
                                      border_width=1, border_color=COLORS["border"])
        self.image_box.grid(row=1, column=0, sticky="nsew", padx=13, pady=(0, 10))
        self.image_box.grid_columnconfigure(0, weight=1)
        self.image_box.grid_rowconfigure(0, weight=1)
        self.preview_label = ctk.CTkLabel(self.image_box, text="选择 PNG 或 JPEG 文件",
                                          font=("Microsoft YaHei UI", 10), text_color=COLORS["subtle"])
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.preview_path_var = ctk.StringVar(value="")
        self.preview_detail_var = ctk.StringVar(value="")
        ctk.CTkLabel(preview, textvariable=self.preview_path_var, wraplength=400, justify="left",
                     font=("Microsoft YaHei UI", 9, "bold"), text_color=COLORS["text"]).grid(row=2, column=0, sticky="ew", padx=16)
        ctk.CTkLabel(preview, textvariable=self.preview_detail_var, wraplength=400, justify="left",
                     font=("Microsoft YaHei UI", 9), text_color=COLORS["muted"]).grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 14))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=23, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        self.status_var = ctk.StringVar(value="")
        ctk.CTkLabel(footer, textvariable=self.status_var, font=("Microsoft YaHei UI", 9),
                     text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(footer, text="Ctrl/Shift 可多选", font=("Microsoft YaHei UI", 9),
                     text_color=COLORS["subtle"]).grid(row=0, column=1, sticky="e")

    def _queue_banner_resize(self, event) -> None:
        width, height = max(1, event.width), max(1, event.height)
        if (width, height) == self.banner_last_size:
            return
        if self.banner_resize_job is not None:
            try:
                self.after_cancel(self.banner_resize_job)
            except Exception:
                pass
        self.banner_resize_job = self.after(90, lambda: self._set_banner_background(width, height))

    def _set_banner_background(self, width: int, height: int) -> None:
        if not hasattr(self, "banner_canvas") or not self.banner_canvas.winfo_exists():
            return
        size = (max(1, width), max(1, height))
        if size == self.banner_last_size and self.banner_photo is not None:
            return
        banner = muramasa_banner(self.app.theme_bg_source, size)
        old_banner = self.banner_photo
        self.banner_canvas.delete("all")
        photo = ImageTk.PhotoImage(banner, master=self.banner_canvas)
        self.banner_canvas.create_image(0, 0, image=photo, anchor="nw")
        self.banner_canvas.create_text(25, 12, text="存档目录", fill=COLORS["text"],
                                       anchor="nw", font=("Yu Mincho", 18, "bold"))
        self.banner_canvas.create_text(25, 43, text=Path(self.archive_path).name,
                                       fill=COLORS["muted"], anchor="nw",
                                       font=("Segoe UI", 9))
        self.banner_info_item = self.banner_canvas.create_text(
            width - 25, height // 2, text=self.header_info_text,
            fill=COLORS["paper"], anchor="e", font=("Microsoft YaHei UI", 9, "bold"))
        self.banner_canvas.create_line(22, height - 2, width - 22, height - 2,
                                       fill=COLORS["accent"], width=2)
        self.banner_photo = photo
        self.banner_last_size = size
        self.banner_resize_job = None

    def _load_worker(self) -> None:
        try:
            info = MURAMASA.list_archive_entries(self.archive_path, self.requested_profile, self.encoding)
            self.events.put(("loaded", info))
        except Exception as exc:
            self.events.put(("error", str(exc), traceback.format_exc()))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "loaded":
                    self._loaded(event[1])
                elif event[0] == "error":
                    self._set_status("读取失败")
                    self._clear_preview(event[1], "")
                    self.app._append_log(f"[错误] {event[1]}")
                elif event[0] == "preview":
                    self._display_preview(*event[1:])
                elif event[0] == "preview_error":
                    self._display_preview_error(*event[1:])
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(100, self._poll_events)

    def _loaded(self, info: dict) -> None:
        self.info = info
        self.entries = info["entries"]
        profile_name = PROFILE_NAMES.get(info["profile"], info["profile_name"])
        self.header_info_text = f"{profile_name}  ·  {info['file_count']:,} 个文件  ·  {format_size(info['archive_size'])}"
        self.banner_canvas.itemconfigure(self.banner_info_item, text=self.header_info_text)
        self.app.profile_result_var.set(f"版本：{profile_name}")
        self.app.count_result_var.set(f"{info['file_count']:,} 个文件")
        self.app.size_result_var.set(format_size(info["archive_size"]))
        self.app.status_var.set(f"已载入目录 · {info['file_count']:,} 个文件")
        self.app._append_log(f"[目录] {profile_name} · {info['file_count']:,} 个文件 · {format_size(info['archive_size'])}")
        self._rebuild_tree()
        self._set_status(f"共 {info['directory_count']:,} 个目录、{info['file_count']:,} 个文件")

    def _ensure_folder(self, folder_path: str) -> str:
        parent = ""
        pieces = [piece for piece in folder_path.split("/") if piece]
        current = []
        for piece in pieces:
            current.append(piece)
            path = "/".join(current)
            iid = self.folder_iids.get(path)
            if iid is None:
                iid = f"d{len(self.folder_iids)}"
                self.folder_iids[path] = iid
                self.tree_items[iid] = {"is_dir": True, "path": path}
                self.tree.insert(parent, "end", iid=iid, text=piece,
                                 values=("", "目录"), open=(len(current) == 1))
            parent = iid
        return parent

    def _rebuild_tree(self, *_args) -> None:
        self.tree.delete(*self.tree.get_children())
        self.folder_iids.clear()
        self.tree_items.clear()
        self.file_iids.clear()
        self.visible_file_iids.clear()
        query = self.search_var.get().strip().casefold()
        files = [entry for entry in self.entries if not entry["is_dir"] and
                 (not query or query in entry["path"].casefold())]
        directories = [entry for entry in self.entries if entry["is_dir"] and
                       (not query or query in entry["path"].casefold() or
                        any(file["path"].casefold().startswith(entry["path"].casefold().rstrip("\\/") + "\\") or
                            file["path"].casefold().startswith(entry["path"].casefold().rstrip("\\/") + "/")
                            for file in files))]

        for entry in directories:
            self._ensure_folder(entry["path"].replace("\\", "/").strip("/"))
        for entry in files:
            normalized = entry["path"].replace("\\", "/").strip("/")
            parent_path, _, name = normalized.rpartition("/")
            parent = self._ensure_folder(parent_path) if parent_path else ""
            iid = f"f{entry['index']}"
            extension = entry["extension"].lstrip(".").upper() or "文件"
            self.tree_items[iid] = {"is_dir": False, "path": entry["path"], "entry": entry}
            self.file_iids[entry["index"]] = iid
            self.visible_file_iids.append(iid)
            self.tree.insert(parent, "end", iid=iid, text=name,
                             values=(format_size(entry["size"]), extension))
        self.selection_var.set(f"显示 {len(files):,} 个文件 · 已选 0 个")
        self.selected_paths = []
        self.extract_selected_button.configure(state="disabled")

    def _search_changed(self, _event=None) -> None:
        if self.info is not None:
            self._rebuild_tree()

    def _selected_file_paths(self) -> list[str]:
        selected = set()
        for iid in self.tree.selection():
            item = self.tree_items.get(iid)
            if not item:
                continue
            if not item["is_dir"]:
                selected.add(item["path"])
                continue
            prefix = item["path"].replace("\\", "/").rstrip("/") + "/"
            for entry in self.entries:
                if not entry["is_dir"] and entry["path"].replace("\\", "/").startswith(prefix):
                    selected.add(entry["path"])
        return [entry["path"] for entry in self.entries if not entry["is_dir"] and entry["path"] in selected]

    def _selection_changed(self, _event=None) -> None:
        self.selected_paths = self._selected_file_paths()
        self.selection_var.set(f"已选 {len(self.selected_paths):,} 个文件")
        self.extract_selected_button.configure(state="normal" if self.selected_paths else "disabled")
        selected_iids = self.tree.selection()
        if len(selected_iids) == 1:
            item = self.tree_items.get(selected_iids[0])
            if item and not item["is_dir"]:
                self._request_preview(item["entry"])
                return
        self.preview_token += 1
        if self.selected_paths:
            self._clear_preview(f"已选 {len(self.selected_paths):,} 个文件", "选择单个图片可预览。")
        else:
            self._clear_preview("选择 PNG 或 JPEG 文件", "")

    def _request_preview(self, entry: dict) -> None:
        self.preview_token += 1
        token = self.preview_token
        path = entry["path"]
        extension = entry["extension"]
        self.preview_path_var.set(path)
        if extension not in self.IMAGE_EXTENSIONS:
            self._clear_preview("此文件不是可预览图片", f"{extension or '未知格式'} · {format_size(entry['size'])}")
            self.preview_path_var.set(path)
            return
        self._clear_preview("正在读取图片…", f"{extension[1:].upper()} · {format_size(entry['size'])}")
        self.preview_path_var.set(path)
        threading.Thread(target=self._preview_worker, args=(entry, token), daemon=True).start()

    def _preview_worker(self, entry: dict, token: int) -> None:
        try:
            data = MURAMASA.read_archive_entry(
                self.archive_path,
                entry["index"],
                crypto_profile=self.info["profile"],
                file_path_encoding=self.encoding,
            )
            if data[:4] == b"NPSI":
                raise ValueError("NPSI 图像格式暂不支持预览")
            with Image.open(io.BytesIO(data)) as image:
                image.seek(0)
                image.load()
                dimensions = image.size
                image_format = image.format or entry["extension"].lstrip(".").upper()
                preview = image.convert("RGBA")
            self.events.put(("preview", token, entry["path"], preview, dimensions, image_format, len(data)))
        except Exception as exc:
            self.events.put(("preview_error", token, entry["path"], str(exc), entry["size"]))

    def _display_preview(self, token: int, path: str, image: Image.Image,
                         dimensions: tuple[int, int], image_format: str, size: int) -> None:
        if token != self.preview_token:
            return
        image.thumbnail((470, 390), Image.Resampling.LANCZOS)
        preview_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        # Keep the previous image alive until CTkLabel has switched its
        # underlying Tk label to the new PhotoImage.
        self.preview_label.configure(image=preview_image, text="")
        self.preview_ctk_image = preview_image
        self.preview_path_var.set(path)
        self.preview_detail_var.set(f"{dimensions[0]} × {dimensions[1]}  ·  {image_format}  ·  {format_size(size)}")
        self._set_status("预览已载入")

    def _display_preview_error(self, token: int, path: str, error: str, size: int) -> None:
        if token != self.preview_token:
            return
        self._clear_preview("无法预览此图片", f"{error} · {format_size(size)}")
        self.preview_path_var.set(path)

    def _clear_preview(self, message: str, detail: str) -> None:
        # CTkLabel currently leaves its inner tkinter.Label image untouched
        # when configured with image=None. Clear that Tcl image reference
        # before releasing the CTkImage, or later text updates can fail with
        # "image pyimageN doesn't exist".
        previous_image = self.preview_ctk_image
        if self.preview_label.winfo_exists():
            self.preview_label._label.configure(image="")
            self.preview_label.configure(image=None, text=message)
        self.preview_ctk_image = None
        self.preview_path_var.set("")
        self.preview_detail_var.set(detail)

    def _select_all_visible(self) -> None:
        if self.visible_file_iids:
            self.tree.selection_set(self.visible_file_iids)
            self.tree.focus(self.visible_file_iids[0])
            self.tree.see(self.visible_file_iids[0])

    def _extract_selected(self) -> None:
        self.app._extract_selected(self.selected_paths, source=self)

    def set_extract_busy(self, busy: bool) -> None:
        state = "disabled" if busy or not self.selected_paths else "normal"
        self.extract_selected_button.configure(state=state)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        self.app.archive_browser = None


def main() -> None:
    # Japanese paths may not be representable in the active Windows console code page.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    app = MuramasaApp()
    app.mainloop()


if __name__ == "__main__":
    main()
