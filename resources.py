import os
import struct
import sys
import tkinter as tk
import tkinter.font as tkfont

FONT_FILENAME = "vcr-osd-mono-rusvhs-icons.ttf"
_font_cache = {}
_registered_font_path = None
_font_family = None


def _base_dirs():
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(meipass)
        candidates.append(os.path.dirname(sys.executable))
    candidates.append(os.path.dirname(os.path.abspath(__file__)))
    return candidates


def resolve_assets_dir():
    for base_dir in _base_dirs():
        assets_dir = os.path.join(base_dir, "assets")
        if os.path.isfile(os.path.join(assets_dir, "background.png")):
            return assets_dir
    tried = "\n".join(f"- {os.path.join(b, 'assets')}" for b in _base_dirs())
    raise FileNotFoundError(
        "Не найдена папка assets (и/или background.png).\n\n"
        f"Пробовал пути:\n{tried}"
    )


def resolve_font_path():
    for base_dir in _base_dirs():
        path = os.path.join(base_dir, "fonts", FONT_FILENAME)
        if os.path.isfile(path):
            return path
    return None


def _read_ttf_family_name(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None

    num_tables = struct.unpack(">H", data[4:6])[0]
    name_offset = None
    for i in range(num_tables):
        rec = 12 + i * 16
        if data[rec : rec + 4] == b"name":
            name_offset = struct.unpack(">I", data[rec + 8 : rec + 12])[0]
            break
    if name_offset is None:
        return None

    storage = struct.unpack(">H", data[name_offset + 4 : name_offset + 6])[0]
    count = struct.unpack(">H", data[name_offset + 2 : name_offset + 4])[0]
    string_offset = name_offset + storage

    for i in range(count):
        rec = name_offset + 6 + i * 12
        platform, _encoding, _language, name_id, length, offset = struct.unpack(
            ">HHHHHH", data[rec : rec + 12]
        )
        if name_id != 1:
            continue
        raw = data[string_offset + offset : string_offset + offset + length]
        if platform == 3:
            return raw.decode("utf-16-be", errors="replace")
        return raw.decode("latin-1", errors="replace")
    return None


def _register_font(path):
    global _registered_font_path, _font_family

    if _registered_font_path == path and _font_family:
        return _font_family

    family = _read_ttf_family_name(path)
    if not family:
        return None

    if sys.platform == "win32":
        try:
            import ctypes

            added = ctypes.windll.gdi32.AddFontResourceExW(os.path.abspath(path), 0x10, 0)
            if added <= 0:
                return None
        except Exception:
            return None

    _registered_font_path = path
    _font_family = family
    return family


def get_font(root, size, weight="normal"):
    key = (id(root), size, weight)
    if key in _font_cache:
        return _font_cache[key]

    path = resolve_font_path()
    family = _register_font(path) if path else None

    if family:
        try:
            font = tkfont.Font(root=root, family=family, size=size)
            if weight == "bold":
                font.configure(weight="bold")
        except tk.TclError:
            font = tkfont.Font(root=root, family="Arial", size=size, weight=weight)
    else:
        font = tkfont.Font(root=root, family="Arial", size=size, weight=weight)

    _font_cache[key] = font
    return font


def load_photo(assets_dir, filename):
    path = os.path.join(assets_dir, filename)
    if not os.path.isfile(path):
        return None
    try:
        return tk.PhotoImage(file=path)
    except tk.TclError:
        return None
