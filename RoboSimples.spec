# -*- mode: python ; coding: utf-8 -*-

"""
Arquivo de configuração do PyInstaller (.spec)
Projeto: Robô Simples Nacional - Automação de Consultas
"""

block_cipher = None

a = Analysis(
    ['main.py'],  # Arquivo principal que inicia a interface Tkinter
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pandas',
        'openpyxl',
        'fpdf',
        'playwright',
        'playwright.async_api',
        'tkinter',
        'queue',
        'threading',
        'subprocess',
        're',
        'json'
    ],
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
    name='Robo_SimplesNacional',  # Nome do arquivo executável final (.exe)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False remove a tela preta do console; mude para True se precisar depurar erros
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # Para adicionar um ícone futuramente, insira o caminho do arquivo .ico aqui
)