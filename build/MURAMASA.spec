# PyInstaller one-file windowed build.
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
project_root = Path(SPECPATH).parent
resources = [
    (project_root / "assets" / "icons" / "muramasa.ico", "assets/icons"),
    (project_root / "assets" / "images" / "title_background.png", "assets/images"),
    (project_root / "assets" / "images" / "logo.png", "assets/images"),
]
for resource, destination in resources:
    if not resource.is_file():
        raise FileNotFoundError(f"Required application resource is missing: {resource}")
    ctk_datas.append((str(resource), destination))

source_dir = project_root / "src"
entry_point = source_dir / "MURAMASA_GUI.py"

a = Analysis(
    [str(entry_point)],
    pathex=[str(source_dir)],
    binaries=ctk_binaries,
    datas=ctk_datas,
    hiddenimports=ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MURAMASA-Extractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icons" / "muramasa.ico"),
)
