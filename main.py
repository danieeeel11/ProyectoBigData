"""Punto de entrada para ejecutar las etapas principales del proyecto."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from urllib.error import URLError

RAIZ = Path(__file__).resolve().parent
SCRIPTS = RAIZ / "scripts"

ACCIONES = {
    "ingesta": (
        "Ingesta BTS + cálculo CO2",
        [sys.executable, str(SCRIPTS / "flujo_ingesta_prefect.py")],
    ),
    "clima": (
        "Descargar clima",
        [sys.executable, str(SCRIPTS / "descargar_clima_openmeteo.py")],
    ),
    "volumen": (
        "Medir volumen de entrada",
        [sys.executable, str(SCRIPTS / "medir_volumen_entrada.py")],
    ),
    "calcular": (
        "Calcular CO2 y verificar cifras",
        [sys.executable, str(SCRIPTS / "calcular_co2.py")],
    ),
    "prefect-server": ("Iniciar servidor Prefect", ["prefect", "server", "start"]),
    "aws-check": (
        "Validar CSV para AWS (sin conexión)",
        [sys.executable, str(SCRIPTS / "subir_resultados_aws.py"), "--dry-run"],
    ),
    "aws-upload": (
        "Subir resultados agregados a AWS",
        [sys.executable, str(SCRIPTS / "subir_resultados_aws.py")],
    ),
    "auditoria": (
        "Auditar calidad de datos (solo lectura)",
        [sys.executable, str(SCRIPTS / "auditar_calidad_rodaje.py")],
    ),
}


def ejecutar(accion: str, pausa: bool = False) -> int:
    """Ejecuta un script conservando la salida y el código de retorno."""
    if accion == "prefect-server":
        return iniciar_en_terminal(
            "Servidor Prefect",
            [sys.executable, "-m", "prefect", "server", "start"],
            RAIZ,
            "http://127.0.0.1:4200",
            "python -m prefect server start",
        )
    if accion == "dask":
        nombre = "Benchmark Dask"
        comando = [sys.executable, str(SCRIPTS / "benchmark_dask.py")]
        if pausa:
            comando.append("--pausa")
        directorio = RAIZ
    elif accion == "dashboard":
        return iniciar_en_terminal(
            "Dashboard local",
            [sys.executable, "app.py"],
            RAIZ / "dashboard",
            "http://127.0.0.1:8050",
            "python app.py (desde la carpeta dashboard)",
        )
    else:
        nombre, comando = ACCIONES[accion]
        directorio = RAIZ

    print(f"\n== {nombre} ==\n", flush=True)
    try:
        resultado = subprocess.run(comando, cwd=directorio, check=False)
    except FileNotFoundError as error:
        print(f"No se pudo iniciar {nombre}: {error}", file=sys.stderr)
        return 1

    if resultado.returncode:
        print(f"\nLa etapa terminó con código {resultado.returncode}.", file=sys.stderr)
    return resultado.returncode


def iniciar_en_terminal(
    nombre: str,
    comando: list[str],
    directorio: Path,
    url: str,
    comando_manual: str,
) -> int:
    """Abre una terminal nueva y ejecuta un comando desde el directorio indicado."""
    comando_shell = shlex.join(comando)

    if sys.platform == "darwin":
        comando_apple_script = (
            comando_shell.replace("\\", "\\\\").replace('"', '\\"')
        )
        launcher = [
            "osascript",
            "-e",
            f'tell application "Terminal" to do script "cd {shlex.quote(str(directorio))} && {comando_apple_script}"',
        ]
    elif os.name == "nt":
        launcher = [
            "cmd.exe",
            "/c",
            "start",
            nombre,
            "cmd.exe",
            "/k",
            f'cd /d "{directorio}" && {subprocess.list2cmdline(comando)}',
        ]
    else:
        terminales = (
            ("x-terminal-emulator", ["-e", "sh", "-lc", comando_shell]),
            ("gnome-terminal", ["--", "sh", "-lc", comando_shell]),
            ("konsole", ["-e", "sh", "-lc", comando_shell]),
            ("xterm", ["-e", "sh", "-lc", comando_shell]),
        )
        launcher = None
        for terminal, argumentos in terminales:
            ejecutable = shutil.which(terminal)
            if ejecutable:
                launcher = [ejecutable, *argumentos]
                break
        if launcher is None:
            print(
                "No encontré una aplicación de terminal compatible. "
                f"Ejecuta manualmente desde {directorio}: {comando_manual}",
                file=sys.stderr,
            )
            return 1

    print(f"\n== Iniciando {nombre} en una terminal nueva ==\n", flush=True)
    try:
        subprocess.Popen(launcher, cwd=directorio)
    except OSError as error:
        print(f"No se pudo abrir una terminal para {nombre}: {error}", file=sys.stderr)
        return 1

    try:
        abrir_navegador_cuando_disponible(url)
    except OSError as error:
        print(f"No se pudo programar la apertura del navegador: {error}", file=sys.stderr)
        print(f"Abre manualmente: {url}")
        return 1

    print(f"{nombre} se ejecuta en la nueva terminal; se abrirá {url} cuando esté disponible.")
    return 0


def abrir_navegador_cuando_disponible(url: str) -> None:
    """Espera en un proceso separado a que un servicio local responda y abre su URL."""
    codigo = """
import sys
import time
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

url = sys.argv[1]
limite = time.monotonic() + 120
while time.monotonic() < limite:
    try:
        with urlopen(url, timeout=2):
            webbrowser.open_new_tab(url)
        break
    except (URLError, TimeoutError):
        time.sleep(1)
"""
    opciones = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        opciones["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        opciones["start_new_session"] = True

    subprocess.Popen([sys.executable, "-c", codigo, url], **opciones)


def mostrar_menu() -> int:
    opciones = [
        ("1", "Ingesta BTS + cálculo CO2", "ingesta"),
        ("2", "Descargar clima", "clima"),
        ("3", "Medir volumen ZIP", "volumen"),
        ("4", "Calcular CO2 + verificar cifras", "calcular"),
        ("5", "Iniciar servidor Prefect", "prefect-server"),
        ("6", "Benchmark Dask", "dask"),
        ("7", "Validar CSV para AWS (dry-run)", "aws-check"),
        ("8", "Subir resultados agregados a AWS", "aws-upload"),
        ("9", "Auditoría de calidad (solo lectura)", "auditoria"),
        ("10", "Desplegar dashboard local", "dashboard"),
    ]

    while True:
        print("\nProyecto Big Data — Rodaje en tierra y CO2")
        for numero, descripcion, _ in opciones:
            print(f"{numero}. {descripcion}")
        print("0. Salir")

        try:
            seleccion = input("Selecciona una etapa: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if seleccion == "0":
            return 0

        opcion = next((op for op in opciones if op[0] == seleccion), None)
        if opcion is None:
            print("Opción no válida. Selecciona uno de los números del menú.")
            continue

        pausa = False
        if opcion[2] == "dask":
            respuesta = input("¿Esperar para capturar el dashboard? [s/N]: ").strip().lower()
            pausa = respuesta in {"s", "si", "sí"}

        codigo = ejecutar(opcion[2], pausa=pausa)
        if codigo:
            print("Revisa el mensaje anterior y vuelve a ejecutar la etapa cuando esté corregido.")


def main(argv: Sequence[str] | None = None) -> int:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(RAIZ / "requirements.txt")])
    parser = argparse.ArgumentParser(
        description="Menú y comandos para ejecutar las etapas del proyecto."
    )
    parser.add_argument(
        "accion",
        nargs="?",
        choices=[*ACCIONES, "dask", "dashboard"],
        help="Etapa a ejecutar; si se omite, se abre el menú interactivo.",
    )
    parser.add_argument(
        "--pausa",
        action="store_true",
        help="En Dask, espera ENTER para permitir capturar el dashboard.",
    )
    argumentos = parser.parse_args(argv)

    if argumentos.pausa and argumentos.accion != "dask":
        parser.error("--pausa solo se puede usar con la acción dask")
    if argumentos.accion is None:
        return mostrar_menu()
    return ejecutar(argumentos.accion, pausa=argumentos.pausa)


if __name__ == "__main__":
    raise SystemExit(main())
