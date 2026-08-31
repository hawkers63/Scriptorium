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
* To give the window a custom icon, drop a scriptorium.ico beside this file and
  set  icon="scriptorium.ico"  in the EXE() call below.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("customtkinter")
hiddenimports = collect_submodules("customtkinter")

# python-docx is optional; bundle its template only if it is installed.
try:
    datas += collect_data_files("docx")
    hiddenimports += collect_submodules("docx")
except Exception:
    pass


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
    runtime_tmpdir=None,
    console=False,          # windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # set to "scriptorium.ico" once you add one
)
