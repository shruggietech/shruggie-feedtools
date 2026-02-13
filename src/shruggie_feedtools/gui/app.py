"""CustomTkinter GUI application.

Two-mode desktop frontend (Parse / Construct / Settings) for shruggie-feedtools.
Calls the same library functions as the CLI.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
import threading
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog
from typing import Any

try:
    import customtkinter as ctk
except ImportError as _exc:  # pragma: no cover
    raise SystemExit(
        "customtkinter is required for the GUI.  Install it with:\n"
        "  pip install shruggie-feedtools[gui]"
    ) from _exc

try:
    from pygments import lex
    from pygments.lexers import JsonLexer
    from pygments.token import Token

    _HAS_PYGMENTS = True
except ImportError:  # pragma: no cover
    _HAS_PYGMENTS = False

try:
    from PIL import Image as PILImage, ImageTk  # type: ignore[import-untyped]
    _HAS_PIL = True
except ImportError:  # pragma: no cover
    _HAS_PIL = False

from shruggie_feedtools._version import __version__
from shruggie_feedtools.utils.logging import (
    disable_file_logging,
    get_log_file_path,
    is_file_logging_enabled,
    setup_file_logging,
)

logger = logging.getLogger("shruggie_feedtools")

# ---------------------------------------------------------------------------
# Theme color palettes
# ---------------------------------------------------------------------------

_THEME_COLORS: dict[str, dict[str, str]] = {
    "dark": {
        "editor_bg": "#1a1a1a",
        "editor_fg": "#d4d4d4",
        "gutter_bg": "#1e1e1e",
        "gutter_fg": "#858585",
        "cursor_color": "#ffffff",
        "select_bg": "#264f78",
        "select_fg": "#d4d4d4",
        "json_key": "#9cdcfe",
        "json_string": "#ce9178",
        "json_number": "#b5cea8",
        "json_const": "#569cd6",
        "json_punct": "#d4d4d4",
    },
    "light": {
        "editor_bg": "#ffffff",
        "editor_fg": "#1e1e1e",
        "gutter_bg": "#f3f3f3",
        "gutter_fg": "#858585",
        "cursor_color": "#000000",
        "select_bg": "#add6ff",
        "select_fg": "#1e1e1e",
        "json_key": "#0451a5",
        "json_string": "#a31515",
        "json_number": "#098658",
        "json_const": "#0000ff",
        "json_punct": "#1e1e1e",
    },
}


def _set_windows_appusermodelid() -> None:
    """Set the Windows AppUserModelID so the taskbar groups our icon."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "com.shruggie.feedtools"
        )
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Font helpers (§12.6 / Appendix A.5)
# ---------------------------------------------------------------------------

_MONO_FAMILY = "JetBrains Mono"
_MONO_FALLBACK = "Consolas"
_SANS_FAMILY = "Inter"
_SANS_FALLBACK = "Segoe UI"
_TITLE_FAMILY = "Space Grotesk"

_FONT_SIZE_DEFAULT = 13
_FONT_SIZE_MIN = 8
_FONT_SIZE_MAX = 32


def _pick_font(preferred: str, fallback: str, size: int = 13) -> ctk.CTkFont:
    """Return a CTkFont trying *preferred* first, then *fallback*."""
    # CTkFont gracefully falls back if a family isn't installed, so we just
    # rely on the OS font matcher.  We still set up the chain here for clarity.
    try:
        return ctk.CTkFont(family=preferred, size=size)
    except Exception:
        return ctk.CTkFont(family=fallback, size=size)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class ShruggieFeedToolsApp(ctk.CTk):
    """Main application window."""

    def __init__(self) -> None:
        # Set Windows taskbar identity BEFORE creating the window
        _set_windows_appusermodelid()

        super().__init__()

        # Theme management — default to dark
        self._current_theme_mode = "Dark"  # "System", "Light", "Dark"
        ctk.set_appearance_mode("dark")

        self.title("Shruggie FeedTools")
        self.minsize(900, 600)
        self.geometry("1100x720")

        # Apply favicon branding (taskbar + title bar)
        self._apply_icon()

        # Logging state
        self._logging_enabled = is_file_logging_enabled()

        # Output font size (user-configurable via Settings)
        self._font_size = _FONT_SIZE_DEFAULT

        # Fonts
        self._mono_font = ctk.CTkFont(family=_MONO_FAMILY, size=self._font_size)
        self._sans_font = ctk.CTkFont(family=_SANS_FAMILY, size=13)
        self._sans_bold = ctk.CTkFont(family=_SANS_FAMILY, size=13, weight="bold")
        self._title_font = ctk.CTkFont(family=_TITLE_FAMILY, size=15, weight="bold")

        # Threading guard
        self._busy = False

        # ---- Layout --------------------------------------------------------
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_work_area()

        # Start in Parse mode
        self._show_parse()

        logger.debug("GUI application initialized (version %s)", __version__)

    # -----------------------------------------------------------------------
    # Branding — favicon
    # -----------------------------------------------------------------------

    def _apply_icon(self) -> None:
        """Set the window icon from brand/favicon.ico."""
        # Try multiple candidate paths (dev layout, PyInstaller bundle)
        candidates = []
        # PyInstaller bundle: files are extracted to sys._MEIPASS
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "brand" / "favicon.ico")  # type: ignore[attr-defined]
        # Development: relative to this source file
        # app.py is at src/shruggie_feedtools/gui/app.py → parents[3] = project root
        candidates.append(Path(__file__).resolve().parents[3] / "brand" / "favicon.ico")
        # Development: relative to CWD
        candidates.append(Path("brand") / "favicon.ico")

        for icon_path in candidates:
            if icon_path.exists():
                logger.debug("Loading icon from: %s", icon_path)
                try:
                    self.iconbitmap(str(icon_path))
                    # Also set via wm_iconphoto for robust taskbar icon
                    if _HAS_PIL:
                        pil_img = PILImage.open(str(icon_path))  # type: ignore[union-attr]
                        photo = ImageTk.PhotoImage(pil_img)  # type: ignore[union-attr]
                        self.wm_iconphoto(True, photo)
                        # Keep a reference to prevent garbage collection
                        self._icon_photo = photo  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.debug("Failed to set icon from %s: %s", icon_path, exc)
                return

        logger.debug("No favicon.ico found in any candidate path")

    # -----------------------------------------------------------------------
    # Sidebar
    # -----------------------------------------------------------------------

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=150, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            sidebar,
            text="Shruggie\nFeedTools",
            font=self._title_font,
        )
        logo.pack(padx=10, pady=(20, 30))

        self._parse_btn = ctk.CTkButton(
            sidebar,
            text="Parse",
            font=self._sans_bold,
            command=self._show_parse,
        )
        self._parse_btn.pack(padx=10, pady=5, fill="x")

        self._construct_btn = ctk.CTkButton(
            sidebar,
            text="Construct",
            font=self._sans_bold,
            command=self._show_construct,
        )
        self._construct_btn.pack(padx=10, pady=5, fill="x")

        self._settings_btn = ctk.CTkButton(
            sidebar,
            text="Settings",
            font=self._sans_bold,
            command=self._show_settings,
        )
        self._settings_btn.pack(padx=10, pady=5, fill="x")

        ver_label = ctk.CTkLabel(
            sidebar,
            text=f"v{__version__}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        ver_label.pack(side="bottom", padx=10, pady=10)

    # -----------------------------------------------------------------------
    # Working area container
    # -----------------------------------------------------------------------

    def _build_work_area(self) -> None:
        self._work_frame = ctk.CTkFrame(self)
        self._work_frame.grid(row=0, column=1, sticky="nswe", padx=4, pady=4)
        self._work_frame.grid_columnconfigure(0, weight=1)
        self._work_frame.grid_rowconfigure(1, weight=1)

        # Top: mode-specific input panel (row 0)
        self._input_frame = ctk.CTkFrame(self._work_frame)
        self._input_frame.grid(row=0, column=0, sticky="nswe", padx=4, pady=(4, 2))
        self._input_frame.grid_columnconfigure(0, weight=1)

        # Bottom: shared output panel (row 1)
        self._build_output_panel()

    # -----------------------------------------------------------------------
    # Output panel (§12.5) — editable, syntax-highlighted, with line numbers
    # -----------------------------------------------------------------------

    # Pygments token → tag-name map (subset for JSON)
    _TOKEN_TAGS: dict[str, str] = {
        "Token.Name.Tag": "json_key",
        "Token.Literal.String.Double": "json_string",
        "Token.Literal.String.Single": "json_string",
        "Token.Literal.Number.Integer": "json_number",
        "Token.Literal.Number.Float": "json_number",
        "Token.Keyword.Constant": "json_const",      # true / false / null
        "Token.Punctuation": "json_punct",
        "Token.Name.Attribute": "json_key",
    }

    def _build_output_panel(self) -> None:
        out_frame = ctk.CTkFrame(self._work_frame)
        out_frame.grid(row=1, column=0, sticky="nswe", padx=4, pady=(2, 4))
        out_frame.grid_columnconfigure(0, weight=1)
        out_frame.grid_rowconfigure(1, weight=1)

        # Header row
        header = ctk.CTkFrame(out_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we", padx=4, pady=(4, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Output", font=self._sans_bold).grid(
            row=0, column=0, sticky="w"
        )

        col = 1
        self._copy_btn = ctk.CTkButton(
            header, text="Copy", width=70, font=self._sans_font, command=self._copy_output
        )
        self._copy_btn.grid(row=0, column=col, padx=(4, 2)); col += 1

        self._save_btn = ctk.CTkButton(
            header, text="Save", width=70, font=self._sans_font, command=self._save_output
        )
        self._save_btn.grid(row=0, column=col, padx=(2, 2)); col += 1

        self._clear_btn = ctk.CTkButton(
            header, text="Clear", width=70, font=self._sans_font, command=self._clear_output
        )
        self._clear_btn.grid(row=0, column=col, padx=(2, 2)); col += 1

        self._minify_var = False  # toggle state: False=pretty, True=minified
        self._format_toggle_btn = ctk.CTkButton(
            header, text="Minify", width=80, font=self._sans_font,
            command=self._toggle_output_format,
        )
        self._format_toggle_btn.grid(row=0, column=col, padx=(2, 4))

        # Editor area — use a ctk frame so scrollbars theme properly
        colors = self._get_theme_colors()
        self._editor_frame = ctk.CTkFrame(
            out_frame, fg_color=colors["editor_bg"], corner_radius=4,
        )
        self._editor_frame.grid(row=1, column=0, sticky="nswe", padx=4, pady=4)
        self._editor_frame.grid_columnconfigure(1, weight=1)
        self._editor_frame.grid_rowconfigure(0, weight=1)

        # Line numbers gutter
        self._line_numbers = tk.Text(
            self._editor_frame, width=5, padx=4, pady=4,
            bg=colors["gutter_bg"], fg=colors["gutter_fg"], bd=0, highlightthickness=0,
            font=(self._mono_font.cget("family"), self._mono_font.cget("size")),
            state="disabled", takefocus=0, wrap="none",
            cursor="arrow",
        )
        self._line_numbers.grid(row=0, column=0, sticky="ns")

        # Main text widget (editable)
        self._output_box = tk.Text(
            self._editor_frame, padx=6, pady=4, bd=0, highlightthickness=0,
            bg=colors["editor_bg"], fg=colors["editor_fg"],
            insertbackground=colors["cursor_color"],
            selectbackground=colors["select_bg"],
            selectforeground=colors["select_fg"],
            font=(self._mono_font.cget("family"), self._mono_font.cget("size")),
            wrap="none", undo=True,
        )
        self._output_box.grid(row=0, column=1, sticky="nswe")

        # Theme-aware scrollbars (CTkScrollbar auto-adapts to appearance mode)
        self._v_scroll = ctk.CTkScrollbar(
            self._editor_frame, orientation="vertical",
            command=self._sync_scroll_y,
        )
        self._v_scroll.grid(row=0, column=2, sticky="ns")

        self._h_scroll = ctk.CTkScrollbar(
            self._editor_frame, orientation="horizontal",
            command=self._output_box.xview,
        )
        self._h_scroll.grid(row=1, column=1, sticky="we")

        self._output_box.configure(
            yscrollcommand=lambda *a: self._on_output_yscroll(self._v_scroll, *a),
        )
        self._output_box.configure(xscrollcommand=self._h_scroll.set)

        # Configure syntax-highlight tags (VS Code dark+ inspired)
        self._output_box.tag_configure("json_key", foreground=colors["json_key"])
        self._output_box.tag_configure("json_string", foreground=colors["json_string"])
        self._output_box.tag_configure("json_number", foreground=colors["json_number"])
        self._output_box.tag_configure("json_const", foreground=colors["json_const"])
        self._output_box.tag_configure("json_punct", foreground=colors["json_punct"])

        # Re-highlight on edits (debounced)
        self._highlight_pending: str | None = None
        self._output_box.bind("<<Modified>>", self._on_output_modified)
        self._output_box.bind("<KeyRelease>", lambda _e: self._schedule_line_update())
        self._output_box.bind("<Configure>", lambda _e: self._update_line_numbers())

    # ---- Scroll sync -------------------------------------------------------

    def _sync_scroll_y(self, *args: Any) -> None:
        self._output_box.yview(*args)
        self._line_numbers.yview(*args)

    def _on_output_yscroll(self, scrollbar: Any, *args: Any) -> None:
        scrollbar.set(*args)
        self._line_numbers.yview_moveto(args[0])

    # ---- Line numbers ------------------------------------------------------

    def _update_line_numbers(self) -> None:
        self._line_numbers.configure(state="normal")
        self._line_numbers.delete("1.0", "end")
        content = self._output_box.get("1.0", "end-1c")
        line_count = content.count("\n") + 1 if content else 1
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self._line_numbers.insert("1.0", numbers)
        self._line_numbers.configure(state="disabled")
        # Sync scroll position
        self._line_numbers.yview_moveto(self._output_box.yview()[0])

    def _schedule_line_update(self) -> None:
        self.after_idle(self._update_line_numbers)

    # ---- Syntax highlighting -----------------------------------------------

    def _apply_json_highlighting(self) -> None:
        """Apply Pygments-based JSON syntax highlighting to the output box."""
        if not _HAS_PYGMENTS:
            return
        # Remove old tags
        for tag_name in self._TOKEN_TAGS.values():
            self._output_box.tag_remove(tag_name, "1.0", "end")
        content = self._output_box.get("1.0", "end-1c")
        if not content.strip():
            return
        try:
            lexer = JsonLexer()  # type: ignore[possibly-unbound]
            tokens = lex(content, lexer)  # type: ignore[possibly-unbound]
            index = "1.0"
            for tok_type, tok_value in tokens:
                end_index = self._output_box.index(f"{index}+{len(tok_value)}c")
                tag_name = self._TOKEN_TAGS.get(str(tok_type))
                if tag_name:
                    self._output_box.tag_add(tag_name, index, end_index)
                index = end_index
        except Exception:
            pass  # If highlighting fails, text is still readable

    def _on_output_modified(self, _event: Any = None) -> None:
        if self._output_box.edit_modified():
            self._output_box.edit_modified(False)
            # Debounce highlighting
            if self._highlight_pending:
                self.after_cancel(self._highlight_pending)
            self._highlight_pending = self.after(150, self._do_rehighlight)

    def _do_rehighlight(self) -> None:
        self._highlight_pending = None
        self._apply_json_highlighting()
        self._update_line_numbers()

    # ---- Output read/write -------------------------------------------------

    def _set_output(self, text: str) -> None:
        self._output_box.delete("1.0", "end")
        self._output_box.insert("1.0", text)
        self._output_box.edit_modified(False)
        self._output_box.edit_reset()  # Clear undo stack for new content
        self._apply_json_highlighting()
        self._update_line_numbers()

    def _clear_output(self) -> None:
        self._set_output("")

    def _copy_output(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._output_box.get("1.0", "end-1c"))

    def _save_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(
                self._output_box.get("1.0", "end-1c") + "\n",
                encoding="utf-8",
            )

    def _toggle_output_format(self) -> None:
        """Toggle output between pretty-printed and minified JSON."""
        content = self._output_box.get("1.0", "end-1c").strip()
        if not content:
            return
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return  # Not valid JSON — do nothing
        if self._minify_var:
            # Currently minified → pretty-print
            self._set_output(json.dumps(data, indent=2, ensure_ascii=False))
            self._format_toggle_btn.configure(text="Minify")
            self._minify_var = False
        else:
            # Currently pretty → minify
            self._set_output(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
            self._format_toggle_btn.configure(text="Pretty")
            self._minify_var = True

    # -----------------------------------------------------------------------
    # Mode switching
    # -----------------------------------------------------------------------

    # Attributes created by mode-specific build methods; cleaned up on switch.
    _MODE_ATTRS_PARSE = (
        "_parse_action_btn", "_parse_method", "_parse_input_area",
        "_url_entry", "_file_path_var", "_batch_text",
        "_pretty_var", "_max_items_var", "_ssl_var",
    )
    _MODE_ATTRS_CONSTRUCT = (
        "_construct_action_btn", "_tmpl_path_var", "_tmpl_title_label",
        "_construct_text", "_timestamp_var",
    )
    _MODE_ATTRS_SETTINGS = (
        "_theme_selector", "_logging_switch", "_log_path_label",
        "_font_size_var", "_font_size_spinbox",
    )

    def _clear_input_frame(self) -> None:
        for child in self._input_frame.winfo_children():
            child.destroy()
        # Remove stale references so hasattr / winfo_exists checks stay correct
        for attr in (*self._MODE_ATTRS_PARSE, *self._MODE_ATTRS_CONSTRUCT, *self._MODE_ATTRS_SETTINGS):
            with contextlib.suppress(AttributeError):
                delattr(self, attr)

    def _show_parse(self) -> None:
        logger.debug("Switching to Parse mode")
        self._clear_input_frame()
        self._build_parse_view()

    def _show_construct(self) -> None:
        logger.debug("Switching to Construct mode")
        self._clear_input_frame()
        self._build_construct_view()

    def _show_settings(self) -> None:
        logger.debug("Switching to Settings mode")
        self._clear_input_frame()
        self._build_settings_view()

    # -----------------------------------------------------------------------
    # Parse mode (§12.3)
    # -----------------------------------------------------------------------

    def _build_parse_view(self) -> None:
        frame = self._input_frame
        frame.grid_columnconfigure(0, weight=1)

        # -- Input method radio buttons --------------------------------------
        method_frame = ctk.CTkFrame(frame, fg_color="transparent")
        method_frame.grid(row=0, column=0, sticky="we", padx=8, pady=(8, 4))

        ctk.CTkLabel(method_frame, text="Input Method:", font=self._sans_bold).pack(
            side="left", padx=(0, 10)
        )

        self._parse_method = ctk.StringVar(value="url")

        for value, label in [("url", "URL"), ("file", "File"), ("batch", "Batch")]:
            ctk.CTkRadioButton(
                method_frame,
                text=label,
                variable=self._parse_method,
                value=value,
                font=self._sans_font,
                command=self._on_parse_method_change,
            ).pack(side="left", padx=6)

        # -- Dynamic input area ----------------------------------------------
        self._parse_input_area = ctk.CTkFrame(frame, fg_color="transparent")
        self._parse_input_area.grid(row=1, column=0, sticky="nswe", padx=8, pady=2)
        self._parse_input_area.grid_columnconfigure(0, weight=1)

        self._build_parse_url_input()

        # -- Options bar -----------------------------------------------------
        opts_frame = ctk.CTkFrame(frame, fg_color="transparent")
        opts_frame.grid(row=2, column=0, sticky="we", padx=8, pady=4)

        self._pretty_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts_frame,
            text="Pretty print",
            variable=self._pretty_var,
            font=self._sans_font,
        ).pack(side="left", padx=(0, 14))

        ctk.CTkLabel(opts_frame, text="Max items:", font=self._sans_font).pack(
            side="left", padx=(0, 4)
        )
        self._max_items_var = ctk.StringVar(value="")
        max_entry = ctk.CTkEntry(
            opts_frame, textvariable=self._max_items_var, width=60, font=self._sans_font
        )
        max_entry.pack(side="left", padx=(0, 14))

        self._ssl_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts_frame,
            text="SSL verify",
            variable=self._ssl_var,
            font=self._sans_font,
        ).pack(side="left", padx=(0, 14))

        # -- Action button ---------------------------------------------------
        action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="e", padx=8, pady=(4, 8))

        self._parse_action_btn = ctk.CTkButton(
            action_frame,
            text="▶  Parse Feed",
            font=self._sans_bold,
            width=160,
            command=self._run_parse,
        )
        self._parse_action_btn.pack(side="right")

    # -- Parse input sub-views -----------------------------------------------

    def _clear_parse_input_area(self) -> None:
        for child in self._parse_input_area.winfo_children():
            child.destroy()

    def _on_parse_method_change(self) -> None:
        method = self._parse_method.get()
        self._clear_parse_input_area()
        if method == "url":
            self._build_parse_url_input()
        elif method == "file":
            self._build_parse_file_input()
        elif method == "batch":
            self._build_parse_batch_input()

    def _build_parse_url_input(self) -> None:
        area = self._parse_input_area
        ctk.CTkLabel(area, text="URL:", font=self._sans_font).grid(
            row=0, column=0, sticky="w", pady=2
        )
        self._url_entry = ctk.CTkEntry(area, font=self._sans_font)
        self._url_entry.grid(row=1, column=0, sticky="we", pady=2)

    def _build_parse_file_input(self) -> None:
        area = self._parse_input_area
        ctk.CTkLabel(area, text="File:", font=self._sans_font).grid(
            row=0, column=0, sticky="w", pady=2
        )
        row = ctk.CTkFrame(area, fg_color="transparent")
        row.grid(row=1, column=0, sticky="we", pady=2)
        row.grid_columnconfigure(0, weight=1)

        self._file_path_var = ctk.StringVar()
        ctk.CTkEntry(
            row,
            textvariable=self._file_path_var,
            font=self._sans_font,
            state="readonly",
        ).grid(row=0, column=0, sticky="we")

        ctk.CTkButton(
            row,
            text="Browse…",
            width=90,
            font=self._sans_font,
            command=self._browse_parse_file,
        ).grid(row=0, column=1, padx=(6, 0))

    def _browse_parse_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Feed files", "*.xml *.json *.rss *.atom"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self._file_path_var.set(path)

    def _build_parse_batch_input(self) -> None:
        area = self._parse_input_area
        area.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(area, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we", pady=2)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="URLs (one per line):", font=self._sans_font).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            header,
            text="Load from File",
            width=120,
            font=self._sans_font,
            command=self._load_batch_file,
        ).grid(row=0, column=1)

        self._batch_text = ctk.CTkTextbox(area, font=self._mono_font, height=100)
        self._batch_text.grid(row=1, column=0, sticky="nswe", pady=2)

    def _load_batch_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            content = Path(path).read_text(encoding="utf-8")
            self._batch_text.delete("1.0", "end")
            self._batch_text.insert("1.0", content)

    # -- Parse execution -----------------------------------------------------

    def _get_parse_config(self) -> dict[str, Any]:
        """Collect parse option values into a dict."""
        cfg: dict[str, Any] = {}
        cfg["pretty_print"] = self._pretty_var.get()
        cfg["verify_ssl"] = self._ssl_var.get()
        max_str = self._max_items_var.get().strip()
        if max_str:
            with contextlib.suppress(ValueError):
                cfg["max_items"] = int(max_str)
        return cfg

    def _capture_parse_input(self, method: str) -> dict[str, Any]:
        """Read all widget values on the main thread (thread-safe)."""
        captured: dict[str, Any] = {"method": method}
        if method == "url":
            captured["url"] = self._url_entry.get().strip()
        elif method == "file":
            captured["file"] = self._file_path_var.get().strip()
        elif method == "batch":
            captured["batch_raw"] = self._batch_text.get("1.0", "end").strip()
        return captured

    def _run_parse(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._clear_output()

        method = self._parse_method.get()
        opts = self._get_parse_config()
        # Capture widget values on the main thread before spawning worker
        captured = self._capture_parse_input(method)
        logger.debug("Starting parse: method=%s, opts=%s", method, opts)

        def task() -> None:
            try:
                result = self._do_parse(captured, opts)
                output_text = json.dumps(
                    result, indent=2 if opts.get("pretty_print") else None, ensure_ascii=False
                )
                logger.debug("Parse completed successfully (status=%s)", result.get("status", "?"))
            except Exception as exc:
                logger.error("Parse failed with exception: %s", exc, exc_info=True)
                output_text = json.dumps(
                    {"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False
                )
            self.after(0, lambda: self._finish_operation(output_text))

        threading.Thread(target=task, daemon=True).start()

    def _do_parse(self, captured: dict[str, Any], opts: dict[str, Any]) -> Any:
        from shruggie_feedtools.core.config import ParserConfig
        from shruggie_feedtools.core.parser import parse_file as _pf
        from shruggie_feedtools.core.parser import parse_url as _pu
        from shruggie_feedtools.core.parser import parse_urls as _pus

        config = ParserConfig(
            max_items=opts.get("max_items"),
            verify_ssl=opts.get("verify_ssl", True),
            pretty_print=opts.get("pretty_print", True),
        )

        method = captured["method"]
        logger.debug("_do_parse: method=%s, config=%s", method, config)

        if method == "url":
            url = captured["url"]
            if not url:
                return {"status": "error", "message": "No URL provided."}
            logger.debug("Parsing URL: %s", url)
            return _pu(url, config)

        elif method == "file":
            fp = captured["file"]
            if not fp:
                return {"status": "error", "message": "No file selected."}
            logger.debug("Parsing file: %s", fp)
            return _pf(Path(fp), config)

        elif method == "batch":
            raw = captured["batch_raw"]
            urls = [
                line.strip()
                for line in raw.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if not urls:
                return {"status": "error", "message": "No URLs provided."}
            logger.debug("Batch parsing %d URLs", len(urls))
            results = _pus(urls, config)
            return results

        return {"status": "error", "message": f"Unknown method: {method}"}

    # -----------------------------------------------------------------------
    # Construct mode (§12.4)
    # -----------------------------------------------------------------------

    def _build_construct_view(self) -> None:
        frame = self._input_frame
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        # -- Template picker -------------------------------------------------
        tmpl_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tmpl_frame.grid(row=0, column=0, sticky="we", padx=8, pady=(8, 4))
        tmpl_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tmpl_frame, text="Template:", font=self._sans_font).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )

        self._tmpl_path_var = ctk.StringVar()
        ctk.CTkEntry(
            tmpl_frame,
            textvariable=self._tmpl_path_var,
            font=self._sans_font,
            state="readonly",
        ).grid(row=0, column=1, sticky="we")

        ctk.CTkButton(
            tmpl_frame,
            text="Browse…",
            width=90,
            font=self._sans_font,
            command=self._browse_template,
        ).grid(row=0, column=2, padx=(6, 0))

        self._tmpl_title_label = ctk.CTkLabel(
            tmpl_frame, text="", font=ctk.CTkFont(size=12), text_color="gray"
        )
        self._tmpl_title_label.grid(row=1, column=1, sticky="w", pady=(2, 0))

        # -- Text area -------------------------------------------------------
        ctk.CTkLabel(frame, text="Text:", font=self._sans_font).grid(
            row=1, column=0, sticky="w", padx=8, pady=(4, 0)
        )
        self._construct_text = ctk.CTkTextbox(frame, font=self._mono_font, height=100)
        self._construct_text.grid(row=2, column=0, sticky="nswe", padx=8, pady=2)

        # -- Timestamp -------------------------------------------------------
        ts_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ts_frame.grid(row=3, column=0, sticky="we", padx=8, pady=4)
        ts_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ts_frame, text="Timestamp:", font=self._sans_font).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self._timestamp_var = ctk.StringVar(
            value=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        ctk.CTkEntry(
            ts_frame, textvariable=self._timestamp_var, font=self._sans_font
        ).grid(row=0, column=1, sticky="we")

        # -- Action button ---------------------------------------------------
        action_frame = ctk.CTkFrame(frame, fg_color="transparent")
        action_frame.grid(row=4, column=0, sticky="e", padx=8, pady=(4, 8))

        self._construct_action_btn = ctk.CTkButton(
            action_frame,
            text="▶  Construct Feed",
            font=self._sans_bold,
            width=180,
            command=self._run_construct,
        )
        self._construct_action_btn.pack(side="right")

    def _browse_template(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("Feed template", "*.feedtemplate.json"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self._tmpl_path_var.set(path)
            # Show feed.title from template
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                title = data.get("feed", {}).get("title", "")
                self._tmpl_title_label.configure(text=f"Feed title: {title}" if title else "")
            except Exception:
                self._tmpl_title_label.configure(text="")

    # -- Construct execution -------------------------------------------------

    def _run_construct(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._clear_output()

        tmpl_path = self._tmpl_path_var.get().strip()
        text = self._construct_text.get("1.0", "end").rstrip("\n")
        timestamp = self._timestamp_var.get().strip()
        logger.debug("Starting construct: template=%s, timestamp=%s", tmpl_path, timestamp)

        def task() -> None:
            try:
                result = self._do_construct(tmpl_path, text, timestamp)
                output_text = json.dumps(result, indent=2, ensure_ascii=False)
                logger.debug("Construct completed successfully")
            except Exception as exc:
                logger.error("Construct failed with exception: %s", exc, exc_info=True)
                output_text = json.dumps(
                    {"status": "error", "message": str(exc)}, indent=2, ensure_ascii=False
                )
            self.after(0, lambda: self._finish_operation(output_text))

        threading.Thread(target=task, daemon=True).start()

    def _do_construct(
        self, tmpl_path: str, text: str, timestamp: str
    ) -> dict[str, Any]:
        from shruggie_feedtools.construct import construct

        if not tmpl_path:
            return {"status": "error", "message": "No template selected."}
        if not text.strip():
            return {"status": "error", "message": "No text content provided."}
        if not timestamp:
            return {"status": "error", "message": "No timestamp provided."}

        return construct(text, timestamp, Path(tmpl_path))

    # -----------------------------------------------------------------------
    # Settings mode
    # -----------------------------------------------------------------------

    def _build_settings_view(self) -> None:
        frame = self._input_frame
        frame.grid_columnconfigure(0, weight=1)

        # Section: Application Theme
        theme_header = ctk.CTkLabel(
            frame, text="Application Theme", font=self._sans_bold,
        )
        theme_header.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        theme_desc = ctk.CTkLabel(
            frame,
            text="Choose how the application appears. \"Auto\" follows the operating system setting.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        theme_desc.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        # Map internal mode name to display label
        current_display = {
            "System": "Auto (Default)",
            "Light": "Light",
            "Dark": "Dark",
        }.get(self._current_theme_mode, "Auto (Default)")

        self._theme_selector = ctk.CTkSegmentedButton(
            frame,
            values=["Auto (Default)", "Light", "Dark"],
            command=self._on_theme_change,
            font=self._sans_font,
        )
        self._theme_selector.set(current_display)
        self._theme_selector.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 16))

        # Divider
        div1 = ctk.CTkFrame(frame, height=2, fg_color="gray30")
        div1.grid(row=3, column=0, sticky="we", padx=12, pady=4)

        # Section: Debug Logging
        log_header = ctk.CTkLabel(
            frame, text="Debug Logging", font=self._sans_bold,
        )
        log_header.grid(row=4, column=0, sticky="w", padx=12, pady=(12, 4))

        log_desc = ctk.CTkLabel(
            frame,
            text="When enabled, detailed debug information is written to a log file\n"
                 "located next to the application executable.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left",
        )
        log_desc.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 6))

        switch_frame = ctk.CTkFrame(frame, fg_color="transparent")
        switch_frame.grid(row=6, column=0, sticky="w", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            switch_frame, text="Enable Logging:", font=self._sans_font,
        ).pack(side="left", padx=(0, 10))

        self._logging_switch = ctk.CTkSwitch(
            switch_frame,
            text="",
            command=self._toggle_logging,
            font=self._sans_font,
            onvalue=1,
            offvalue=0,
        )
        if self._logging_enabled:
            self._logging_switch.select()
        else:
            self._logging_switch.deselect()
        self._logging_switch.pack(side="left")

        # Show log file path
        log_path = get_log_file_path()
        self._log_path_label = ctk.CTkLabel(
            frame,
            text=f"Log file: {log_path}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self._log_path_label.grid(row=7, column=0, sticky="w", padx=12, pady=(4, 12))

        # Divider
        div2 = ctk.CTkFrame(frame, height=2, fg_color="gray30")
        div2.grid(row=8, column=0, sticky="we", padx=12, pady=4)

        # Section: Output Font Size
        font_header = ctk.CTkLabel(
            frame, text="Output Font Size", font=self._sans_bold,
        )
        font_header.grid(row=9, column=0, sticky="w", padx=12, pady=(12, 4))

        font_desc = ctk.CTkLabel(
            frame,
            text=f"Set the font size for the output viewer ({_FONT_SIZE_MIN}–{_FONT_SIZE_MAX} pt).",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        font_desc.grid(row=10, column=0, sticky="w", padx=12, pady=(0, 6))

        spin_frame = ctk.CTkFrame(frame, fg_color="transparent")
        spin_frame.grid(row=11, column=0, sticky="w", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            spin_frame, text="Font Size:", font=self._sans_font,
        ).pack(side="left", padx=(0, 10))

        self._font_size_var = tk.IntVar(value=self._font_size)
        self._font_size_spinbox = tk.Spinbox(
            spin_frame,
            from_=_FONT_SIZE_MIN,
            to=_FONT_SIZE_MAX,
            textvariable=self._font_size_var,
            width=5,
            font=(self._sans_font.cget("family"), 13),
            command=self._on_font_size_change,
        )
        self._font_size_spinbox.pack(side="left")
        # Also validate on manual typed entry (Return / FocusOut)
        self._font_size_spinbox.bind("<Return>", lambda _e: self._on_font_size_change())
        self._font_size_spinbox.bind("<FocusOut>", lambda _e: self._on_font_size_change())

    # -----------------------------------------------------------------------
    # Theme management
    # -----------------------------------------------------------------------

    def _get_effective_theme(self) -> str:
        """Return 'dark' or 'light' based on current effective appearance."""
        mode = ctk.get_appearance_mode()  # Returns "Dark" or "Light"
        return mode.lower()

    def _get_theme_colors(self) -> dict[str, str]:
        """Return the color palette for the current effective theme."""
        return _THEME_COLORS.get(self._get_effective_theme(), _THEME_COLORS["dark"])

    def _on_theme_change(self, choice: str) -> None:
        """Handle theme selection change from Settings."""
        mode_map = {
            "Auto (Default)": "System",
            "Light": "Light",
            "Dark": "Dark",
        }
        mode = mode_map.get(choice, "System")
        self._current_theme_mode = mode
        logger.debug("Theme changed to: %s", mode)

        ctk.set_appearance_mode(mode.lower())

        # Update editor area colors after a short delay for CTk to apply
        self.after(50, self._apply_editor_theme)

    def _apply_editor_theme(self) -> None:
        """Update the text editor and gutter colors to match current theme."""
        colors = self._get_theme_colors()
        logger.debug("Applying editor theme: %s", self._get_effective_theme())

        # Update editor frame background
        if hasattr(self, "_editor_frame") and self._widget_alive(self._editor_frame):
            self._editor_frame.configure(fg_color=colors["editor_bg"])

        # Update output text widget
        if hasattr(self, "_output_box") and self._widget_alive(self._output_box):
            self._output_box.configure(
                bg=colors["editor_bg"],
                fg=colors["editor_fg"],
                insertbackground=colors["cursor_color"],
                selectbackground=colors["select_bg"],
                selectforeground=colors["select_fg"],
            )
            # Update syntax-highlight tag colors
            self._output_box.tag_configure("json_key", foreground=colors["json_key"])
            self._output_box.tag_configure("json_string", foreground=colors["json_string"])
            self._output_box.tag_configure("json_number", foreground=colors["json_number"])
            self._output_box.tag_configure("json_const", foreground=colors["json_const"])
            self._output_box.tag_configure("json_punct", foreground=colors["json_punct"])
            # Re-apply highlighting
            self._apply_json_highlighting()

        # Update line numbers gutter
        if hasattr(self, "_line_numbers") and self._widget_alive(self._line_numbers):
            self._line_numbers.configure(
                bg=colors["gutter_bg"],
                fg=colors["gutter_fg"],
            )

    # -----------------------------------------------------------------------
    # Logging toggle
    # -----------------------------------------------------------------------

    def _on_font_size_change(self) -> None:
        """Validate, clamp, and apply the output viewer font size."""
        try:
            raw = self._font_size_var.get()
        except (tk.TclError, ValueError):
            # Non-numeric garbage — reset to current value
            self._font_size_var.set(self._font_size)
            return

        clamped = raw
        if raw < _FONT_SIZE_MIN:
            clamped = _FONT_SIZE_MIN
            logger.debug(
                "Font size %d below minimum; clamped to %d", raw, _FONT_SIZE_MIN,
            )
        elif raw > _FONT_SIZE_MAX:
            clamped = _FONT_SIZE_MAX
            logger.debug(
                "Font size %d above maximum; clamped to %d", raw, _FONT_SIZE_MAX,
            )

        if clamped != raw:
            self._font_size_var.set(clamped)

        if clamped == self._font_size:
            return  # no change

        self._font_size = clamped
        logger.debug("Output font size changed to %d", clamped)
        self._apply_font_size()

    def _apply_font_size(self) -> None:
        """Push the current font size to the output editor and gutter."""
        size = self._font_size
        self._mono_font.configure(size=size)

        if hasattr(self, "_output_box") and self._widget_alive(self._output_box):
            self._output_box.configure(
                font=(self._mono_font.cget("family"), size),
            )
        if hasattr(self, "_line_numbers") and self._widget_alive(self._line_numbers):
            self._line_numbers.configure(
                font=(self._mono_font.cget("family"), size),
            )
        # Refresh line-number widths / scroll
        if hasattr(self, "_update_line_numbers"):
            self.after_idle(self._update_line_numbers)

    def _toggle_logging(self) -> None:
        """Enable or disable debug file logging."""
        if hasattr(self, "_logging_switch"):
            enabled = self._logging_switch.get() == 1
        else:
            enabled = not self._logging_enabled

        if enabled and not self._logging_enabled:
            log_path = setup_file_logging()
            self._logging_enabled = True
            logger.debug("GUI: Debug logging enabled by user")
            logger.debug("Application version: %s", __version__)
        elif not enabled and self._logging_enabled:
            logger.debug("GUI: Debug logging disabled by user")
            disable_file_logging()
            self._logging_enabled = False

    # -----------------------------------------------------------------------
    # Threading helpers (§12.7)
    # -----------------------------------------------------------------------

    @staticmethod
    def _widget_alive(widget: Any) -> bool:
        """Return True if a widget reference points to a live Tk widget."""
        try:
            return widget.winfo_exists()
        except Exception:
            return False

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        # Disable/enable only live action buttons
        for btn in self._find_action_buttons():
            btn.configure(state=state)
            if busy:
                btn.configure(text="⏳  Working…")
        if not busy:
            self._restore_button_labels()

    def _find_action_buttons(self) -> list[ctk.CTkButton]:
        buttons: list[ctk.CTkButton] = []
        for attr in ("_parse_action_btn", "_construct_action_btn"):
            btn = getattr(self, attr, None)
            if btn is not None and self._widget_alive(btn):
                buttons.append(btn)
        return buttons

    def _restore_button_labels(self) -> None:
        if hasattr(self, "_parse_action_btn") and self._widget_alive(self._parse_action_btn):
            self._parse_action_btn.configure(text="▶  Parse Feed")
        if hasattr(self, "_construct_action_btn") and self._widget_alive(self._construct_action_btn):
            self._construct_action_btn.configure(text="▶  Construct Feed")

    def _finish_operation(self, output_text: str) -> None:
        self._set_output(output_text)
        self._set_busy(False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Launch the GUI application."""
    logger.debug("Launching Shruggie FeedTools GUI v%s", __version__)
    app = ShruggieFeedToolsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
