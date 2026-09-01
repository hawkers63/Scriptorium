# -*- mode: python ; coding: utf-8 -*-
r"""
PyInstaller build spec for Scriptorium.

Build a standalone Windows executable with:

    pip install pyinstaller
    pyinstaller scriptorium.spec

The result is  dist\Scriptorium.exe  — a single windowed executable that needs
no separate Python install. Settings (including your API key) are stored under
%LOCALAPPDATA%\Scriptorium when running as the packaged .exe.

Notes
-----
* customtkinter ships data files (its themes/assets); collect_data_files and
  collect_submodules gather them so the packaged app is styled correctly.
* python-docx is optional — its default template is bundled only if the package
  is installed at build time; otherwise the .exe still runs, just without .docx.
* pystray + Pillow are optional too — needed only for "minimise to tray";
  bundled only if installed at build time, same pattern as python-docx.
* icon/Scriptorium-256.ico gives the .exe its taskbar/Explorer icon; both
  .ico files are also bundled as data because the tray icon and the window's
  own iconbitmap() (resource_path() in scriptorium.py) load them via
  PIL/Tk at runtime, not just as a Windows icon resource.
  version_info.txt supplies the FileDescription/ProductVersion etc. shown on
  the .exe's Properties > Details tab. Bump version_info.txt's version numbers
  alongside APP_VERSION in scriptorium.py when cutting a release.
* runtime_tmpdir is pinned under %LOCALAPPDATA%\Scriptorium instead of the
  default shared %TEMP%\_MEIxxxxxx. Diagnosed 2026-09-01: a onefile build
  extracts to %TEMP% and depends on that folder surviving for the life of
  the process (Python lazily pulls some stdlib modules from base_library.zip
  there on first use -- e.g. on the first network request, not at startup).
  A generic "sweep %TEMP%" cleanup tool run while Scriptorium is still open
  deletes it out from under the running process, surfacing as
  "Network error reaching the Claude API: [Errno 2] No such file or
  directory: ...\_MEI########\base_library.zip" the next time such a module
  is needed. %LOCALAPPDATA%\Scriptorium is the same directory the app
  already uses for its own config, and is the one directory most "clean
  temp files" scripts already know to leave alone by name.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

datas = collect_data_files("customtkinter")
hiddenimports = collect_submodules("customtkinter")

datas += [
    ("icon/Scriptorium-256.ico", "icon"),
    ("icon/Scriptorium-96.ico", "icon"),
]

# python-docx is optional; bundle its template only if it is installed.
try:
    datas += collect_data_files("docx")
    hiddenimports += collect_submodules("docx")
except Exception:
    pass

# pystray is optional; bundle its platform backends only if it is installed.
try:
    hiddenimports += collect_submodules("pystray")
except Exception:
    pass

# See "runtime_tmpdir" note above — kept out of the shared, frequently-swept
# %TEMP% so a running instance survives a generic temp/junk cleanup tool.
runtime_tmpdir = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Scriptorium", "runtime")


a = Analysis(
    ["scriptorium.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Scriptorium",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=runtime_tmpdir,
    console=False,          # windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon/Scriptorium-256.ico",
    version="version_info.txt",
)
