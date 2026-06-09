# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Bundle entire packages (data files, binaries, submodules) for tricky deps
for pkg in [
    "pyvista",
    "pyvistaqt",
    "vtkmodules",
    "vtk",
    "pdal",
    "rasterio",
    "fiona",
    "shapely",
    "pyproj",
    "geopandas",
    "matplotlib",
    "skimage",
    "open3d",
    "richdem",
    "pysheds",
    "laspy",
    "lazrs",
    "reportlab",
    "imageio",
    "imageio_ffmpeg",
    "PyQt6",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += collect_submodules("vtkmodules")

# Bundle the resources/ folder (icons, styles, colormaps, models)
datas += [("resources", "resources")]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6", "PySide2", "PyQt5", "shiboken6", "shiboken2"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ALAS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon="resources/icons/alas.ico" if __import__("os").path.exists("resources/icons/alas.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ALAS",
)
