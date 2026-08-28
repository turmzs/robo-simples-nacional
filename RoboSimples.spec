# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Coleta forçada de todos os submódulos e arquivos de dados do pandas e openpyxl
pandas_submodules = collect_submodules('pandas') + collect_submodules('openpyxl')
pandas_datas = collect_data_files('pandas')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=pandas_datas,  # Inclui os arquivos de dados necessários do pandas
    hiddenimports=[
        'fpdf',
        'playwright',
        'playwright.async_api',
        'tkinter',
        'queue',
        'threading',
        'subprocess',
        're',
        'json'
    ] + pandas_submodules,  # Adiciona todos os submódulos coletados
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
    name='Robo_SimplesNacional',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Oculta a janela de console do Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)