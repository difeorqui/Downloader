"""Punto de entrada: ``python -m downloader``."""

import contextlib
import ctypes
import sys
import tkinter as tk

from downloader.ui.app import App


def main() -> None:
    if sys.platform == "win32":
        with contextlib.suppress(AttributeError, OSError):  # texto nítido en pantallas densas
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
