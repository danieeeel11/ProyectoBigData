"""
Mide el volumen de ENTRADA (CSV descomprimido dentro de los ZIP de BTS)
sin tener que descomprimir todo a disco — lee el tamaño real que
reporta cada ZIP en su índice interno.

Esto es lo que hay que documentar en el contrato: el requisito de
1,5 GB aplica a los datos de entrada, no al Parquet final (que es
más pequeño porque está comprimido de forma columnar).

Uso (desde Anaconda Prompt, parado en la carpeta del proyecto):
    conda activate bigdata
    python scripts/medir_volumen_entrada.py
"""

import zipfile
from pathlib import Path

CARPETA_RAW = Path("data/raw")

total_comprimido = 0
total_descomprimido = 0
filas_por_archivo = []

archivos = sorted(CARPETA_RAW.glob("*.zip"))

if not archivos:
    print(f"No encontré archivos .zip en {CARPETA_RAW.resolve()}")
    print("Verifica que estás parada en la carpeta raíz del proyecto.")
else:
    for zip_path in archivos:
        total_comprimido += zip_path.stat().st_size
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                if info.filename.lower().endswith(".csv"):
                    total_descomprimido += info.file_size
                    filas_por_archivo.append((zip_path.name, info.file_size))

    print(f"Archivos ZIP encontrados:        {len(archivos)}")
    print(f"Tamaño total comprimido (ZIP):    {total_comprimido / 1e9:.2f} GB")
    print(f"Tamaño total descomprimido (CSV): {total_descomprimido / 1e9:.2f} GB")
    print()
    if total_descomprimido / 1e9 >= 1.5:
        print(f"OK: cumple el minimo de 1.5 GB exigido por el docente "
              f"({total_descomprimido / 1e9:.2f} GB)")
    else:
        print(f"NO alcanza el minimo de 1.5 GB "
              f"(solo {total_descomprimido / 1e9:.2f} GB)")
