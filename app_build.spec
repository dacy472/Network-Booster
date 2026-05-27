# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'], # The entry point of your application
    pathex=[],
    binaries=[],
    datas=[], # Add non-Python files here in format [('source/file.ext', 'destination_folder')]
    hiddenimports=['requests', 'concurrent.futures', 'tkinter'], # Force inclusion if PyInstaller misses them
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NetworkBooster', # Name of the generated .exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Use UPX compression if installed to make the exe smaller
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # CRITICAL: This hides the background command prompt console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # Example: 'app_icon.ico'
)
