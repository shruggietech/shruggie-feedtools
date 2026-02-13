"""CustomTkinter GUI application.

Two-mode desktop frontend (Parse / Construct) for shruggie-feedtools.
Calls the same library functions as the CLI.
"""

from __future__ import annotations

import contextlib
import json
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

from shruggie_feedtools._version import __version__

# ---------------------------------------------------------------------------
# Font helpers (§12.6 / Appendix A.5)
# ---------------------------------------------------------------------------

_MONO_FAMILY = "JetBrains Mono"
_MONO_FALLBACK = "Consolas"
_SANS_FAMILY = "Inter"
_SANS_FALLBACK = "Segoe UI"
_TITLE_FAMILY = "Space Grotesk"


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
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.title("Shruggie FeedTools")
        self.minsize(900, 600)
        self.geometry("1100x720")

        # Apply favicon branding (taskbar + title bar)
        self._apply_icon()

        # Fonts
        self._mono_font = ctk.CTkFont(family=_MONO_FAMILY, size=13)
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
        candidates.append(Path(__file__).resolve().parents[2] / "brand" / "favicon.ico")
        # Development: relative to CWD
        candidates.append(Path("brand") / "favicon.ico")

        for icon_path in candidates:
            if icon_path.exists():
                try:
                    self.iconbitmap(str(icon_path))
                except Exception:
                    pass
                return

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

        # Editor area — tk.Text with line-number gutter
        editor_frame = tk.Frame(out_frame, bg="#1a1a1a")
        editor_frame.grid(row=1, column=0, sticky="nswe", padx=4, pady=4)
        editor_frame.grid_columnconfigure(1, weight=1)
        editor_frame.grid_rowconfigure(0, weight=1)

        # Line numbers gutter
        self._line_numbers = tk.Text(
            editor_frame, width=5, padx=4, pady=4,
            bg="#1e1e1e", fg="#858585", bd=0, highlightthickness=0,
            font=(self._mono_font.cget("family"), self._mono_font.cget("size")),
            state="disabled", takefocus=0, wrap="none",
            cursor="arrow",
        )
        self._line_numbers.grid(row=0, column=0, sticky="ns")

        # Main text widget (editable)
        self._output_box = tk.Text(
            editor_frame, padx=6, pady=4, bd=0, highlightthickness=0,
            bg="#1a1a1a", fg="#d4d4d4", insertbackground="#ffffff",
            selectbackground="#264f78", selectforeground="#d4d4d4",
            font=(self._mono_font.cget("family"), self._mono_font.cget("size")),
            wrap="none", undo=True,
        )
        self._output_box.grid(row=0, column=1, sticky="nswe")

        # Scrollbars
        v_scroll = tk.Scrollbar(editor_frame, orient="vertical",
                                command=self._sync_scroll_y)
        v_scroll.grid(row=0, column=2, sticky="ns")
        h_scroll = tk.Scrollbar(editor_frame, orient="horizontal",
                                command=self._output_box.xview)
        h_scroll.grid(row=1, column=1, sticky="we")

        self._output_box.configure(yscrollcommand=lambda *a: self._on_output_yscroll(v_scroll, *a))
        self._output_box.configure(xscrollcommand=h_scroll.set)

        # Configure syntax-highlight tags (VS Code dark+ inspired)
        self._output_box.tag_configure("json_key", foreground="#9cdcfe")
        self._output_box.tag_configure("json_string", foreground="#ce9178")
        self._output_box.tag_configure("json_number", foreground="#b5cea8")
        self._output_box.tag_configure("json_const", foreground="#569cd6")
        self._output_box.tag_configure("json_punct", foreground="#d4d4d4")

        # Re-highlight on edits (debounced)
        self._highlight_pending: str | None = None
        self._output_box.bind("<<Modified>>", self._on_output_modified)
        self._output_box.bind("<KeyRelease>", lambda _e: self._schedule_line_update())
        self._output_box.bind("<Configure>", lambda _e: self._update_line_numbers())

    # ---- Scroll sync -------------------------------------------------------

    def _sync_scroll_y(self, *args: Any) -> None:
        self._output_box.yview(*args)
        self._line_numbers.yview(*args)

    def _on_output_yscroll(self, scrollbar: tk.Scrollbar, *args: Any) -> None:
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

    def _clear_input_frame(self) -> None:
        for child in self._input_frame.winfo_children():
            child.destroy()
        # Remove stale references so hasattr / winfo_exists checks stay correct
        for attr in (*self._MODE_ATTRS_PARSE, *self._MODE_ATTRS_CONSTRUCT):
            with contextlib.suppress(AttributeError):
                delattr(self, attr)

    def _show_parse(self) -> None:
        self._clear_input_frame()
        self._build_parse_view()

    def _show_construct(self) -> None:
        self._clear_input_frame()
        self._build_construct_view()

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

        def task() -> None:
            try:
                result = self._do_parse(captured, opts)
                output_text = json.dumps(
                    result, indent=2 if opts.get("pretty_print") else None, ensure_ascii=False
                )
            except Exception as exc:
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

        if method == "url":
            url = captured["url"]
            if not url:
                return {"status": "error", "message": "No URL provided."}
            return _pu(url, config)

        elif method == "file":
            fp = captured["file"]
            if not fp:
                return {"status": "error", "message": "No file selected."}
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

        def task() -> None:
            try:
                result = self._do_construct(tmpl_path, text, timestamp)
                output_text = json.dumps(result, indent=2, ensure_ascii=False)
            except Exception as exc:
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
    app = ShruggieFeedToolsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
