# Guía de ejecución completa — Rodaje en tierra y CO₂ (BTS 2023–2025)

Paso a paso para que **cualquier integrante del grupo** pueda clonar el repo, preparar el ambiente, correr el pipeline y conectar AWS + Grafana.

**Sistema de referencia:** Windows 10/11, Anaconda/Miniconda, Python 3.11, ambiente `bigdata`.  
**Terminal:** usa **Anaconda Prompt** (no PowerShell de Cursor: ahí `conda` suele fallar).

---

## 0. Qué vas a ejecutar (mapa)

```
1. Clonar / abrir el proyecto
2. Ambiente conda + librerías
3. Datos: ZIP BTS → Parquet (si no los tienes)
4. Clima (si falta el CSV)
5. Medir volumen de entrada
6. Calcular CO₂ + pruebas
7. Notebook EDA
8. Prefect (tablero + fallo controlado)
9. Dask (2 configuraciones)
10. AWS RDS (solo tablas agregadas)
11. Grafana (paneles gerenciales)
```

**Nunca subas a GitHub ni a AWS:** ZIP, CSV crudos de BTS, Parquet por vuelo, ni el archivo `.env`.

---

## 1. Abrir el proyecto

### Opción A — Ya tienes el repo clonado

```text
cd C:\Users\TU_USUARIO\Documents\Proyecto\ProyectoBigData
```

(Sustituye la ruta por la tuya. En el equipo de Lina es `C:\Users\linam\Documents\Proyecto\ProyectoBigData`.)

### Opción B — Clonar desde GitHub

1. Abre GitHub Desktop → **Clone repository**.
2. Elige el repo del grupo y una carpeta local.
3. En Anaconda Prompt:

```text
cd RUTA\DEL\ProyectoBigData
```

Comprueba que existan, entre otros:

- `config.py`
- `scripts/calcular_co2.py`
- `scripts/flujo_ingesta_prefect.py`
- `scripts/benchmark_dask.py`
- `scripts/subir_resultados_aws.py`
- `notebooks/eda_rodaje_co2.ipynb`
- `requirements.txt`
- `.env.example`

---

## 2. Ambiente Conda (`bigdata`)

En **Anaconda Prompt**:

```text
conda activate bigdata
```

Si el ambiente no existe:

```text
conda create -n bigdata python=3.11 -y
conda activate bigdata
pip install -r requirements.txt
```

Opcional (notebooks):

```text
pip install nbformat nbclient ipykernel
python -m ipykernel install --user --name bigdata --display-name "Python (bigdata)"
```

Comprueba:

```text
python -c "import pandas, duckdb, dask, prefect, sqlalchemy; print('OK')"
```

---

## 3. Datos de entrada (ZIP y Parquet)

Los ZIP y el Parquet **no van en Git**. Cada persona los necesita en local.

### 3.1 Si ya te pasaron la carpeta `data/`

Debes tener:

| Carpeta | Contenido esperado |
|---|---|
| `data/raw/` | 36 ZIP (2023-01 … 2025-12) |
| `data/parquet/` | Particiones `Year=2023|2024|2025` / `Month=1..12` |
| `data/clima/clima_aeropuertos.csv` | Clima diario (sí puede estar en Git) |
| `data/resultados/` | CSV agregados (sí pueden estar en Git) |

### 3.2 Si no tienes los ZIP: descargarlos con Prefect

El flujo descarga desde BTS (puede tardar mucho la primera vez; necesita internet):

```text
cd RUTA\DEL\ProyectoBigData
conda activate bigdata
python scripts/flujo_ingesta_prefect.py
```

Eso descarga cada mes, convierte a Parquet y al final calcula el CO₂.  
Si un mes ya está, lo **omite** (idempotente).

### 3.3 Solo clima (si falta el CSV)

```text
python scripts/descargar_clima_openmeteo.py
```

Salida: `data/clima/clima_aeropuertos.csv`.

---

## 4. Medir el volumen de entrada (rúbrica > 1,5 GB)

```text
cd RUTA\DEL\ProyectoBigData
conda activate bigdata
python scripts/medir_volumen_entrada.py
```

**Debes ver algo como:**

- 36 ZIP  
- ~1,05 GB comprimido  
- ~9,47 GB descomprimido  
- Cumple el mínimo de 1,5 GB  

---

## 5. Calcular CO₂ y verificar cifras

```text
python scripts/calcular_co2.py
```

El script:

1. Lee todo el Parquet con DuckDB (no carga 21 M de filas en pandas).
2. Escribe CSV en `data/resultados/`.
3. Corre pruebas de exactitud; **si fallan, se detiene**.

**Cifras que deben cuadrar (escenario bajo 6 kg/min):**

| Indicador | Valor |
|---|---:|
| Filas Parquet | 20.928.579 |
| Vuelos ambos tiempos válidos | 20.636.222 |
| Horas de rodaje | 9.057.336 |
| CO₂ total bajo | 10.303.625 t |
| CO₂ total alto (12 kg/min) | 20.607.251 t |

Parámetros modificables: `config.py` (`CONSUMO_KG_MIN_BAJO`, `CONSUMO_KG_MIN_ALTO`, `FACTOR_CO2`, `TAXI_MAX_MIN`).  
No cambies esos números en la entrega final salvo acuerdo del grupo.

Archivos generados (entre otros):

- `data/resultados/resumen_global.csv`
- `data/resultados/co2_aeropuerto_mes.csv`
- `data/resultados/co2_aeropuerto_hora.csv`
- `data/resultados/rodaje_clima.csv`
- `data/resultados/rodaje_clima_independiente.csv`
- `data/resultados/escenario_ahorro.csv`
- `data/resultados/verificacion_exactitud.csv`

---

## 6. Notebook de EDA

1. Abre el proyecto en Cursor o VS Code / Jupyter.
2. `Ctrl+Shift+P` → **Python: Select Interpreter** → ambiente `bigdata`.
3. Abre `notebooks/eda_rodaje_co2.ipynb`.
4. Ejecuta todas las celdas (**Run All**).

Debe mostrar la tabla esperado vs obtenido en `True` y las gráficas de rodaje/CO₂.

---

## 7. Prefect (flujo recurrente)

Necesitas **dos** ventanas de Anaconda Prompt, ambas en la carpeta del proyecto con `conda activate bigdata`.

### Terminal 1 — servidor (déjala abierta)

```text
cd RUTA\DEL\ProyectoBigData
conda activate bigdata
prefect server start
```

Abre el navegador: [http://127.0.0.1:4200](http://127.0.0.1:4200)

### Terminal 2 — corrida normal

```text
cd RUTA\DEL\ProyectoBigData
conda activate bigdata
python scripts/flujo_ingesta_prefect.py
```

**Qué debes ver:**

- Los 36 meses ya convertidos: estado **omitido**.
- Al final: recalcula CO₂ y guarda CSV.
- En el tablero Prefect: flujo `ingesta-y-analitica-bts` en **Completed**.

**Captura:** historial de corridas en http://127.0.0.1:4200 → guárdala en `data/evidencia/`.

### Fallo controlado (Unidad 4)

En la Terminal 2:

```text
python -c "import sys; sys.path.insert(0, 'scripts'); from flujo_ingesta_prefect import flujo_ingesta_bts; import config; flujo_ingesta_bts([(anio, mes) for anio in config.ANIOS for mes in config.MESES], demostrar_fallo=True)"
```

**Qué debes ver en el log:**

- `ZIP corrupto`
- `esquema sin` / faltan `TaxiOut` / `TaxiIn`
- Flujo termina en **Completed** sin borrar el Parquet bueno.

**Captura:** esa corrida en el tablero o el log.

### Segunda corrida con mes nuevo (opcional, evidencia de idempotencia)

Cuando BTS publique un mes nuevo, o para demostrar el patrón, edita temporalmente el final de `scripts/flujo_ingesta_prefect.py` (bloque comentado) o llama el flujo con una lista ampliada. Los meses viejos deben decir **omitido** y el CO₂ se recalcula sobre todo el Parquet.

---

## 8. Dask (benchmark, ≥ 2 configuraciones)

Cierra Chrome/programas pesados si tienes ~16 GB de RAM.

### Sin capturas (rápido)

```text
cd RUTA\DEL\ProyectoBigData
conda activate bigdata
python scripts/benchmark_dask.py
```

### Con capturas del dashboard

```text
python scripts/benchmark_dask.py --pausa
```

1. Copia el enlace que imprime (a veces no es el puerto 8787).
2. Ábrelo en el navegador.
3. Pulsa ENTER en la terminal para calcular.
4. Captura el dashboard.
5. Pulsa ENTER para cerrar esa configuración y pasar a la siguiente.

**Qué debe cuadrar:**

- Config A y Config B con la **misma** `suma_co2_t_bajo` ≈ **7.042.250,7 t** (solo salida con hora; no es el total de 10,3 Mt).
- Archivo: `data/resultados/benchmark_dask.csv`.
- Capturas en `data/evidencia/`.

La Config C solo corre si hay al menos ~8 GB libres; con A y B ya se cumple el requisito.

---

## 9. AWS RDS (solo resultados agregados)

Detalle largo: `docs/guia_aws_grafana.md`. Resumen:

### 9.1 Crear la base (AWS Academy Learner Lab)

1. **Start Lab** (sesión ~4 h; al cerrar se borra todo).
2. Consola AWS → región **us-east-1**.
3. **RDS** → Create database → **PostgreSQL**, `db.t3.micro`, acceso público **Yes**.
4. Usuario/contraseña: anótalos solo en `.env`.
5. Espera estado **Available** y copia el **Endpoint**.

### 9.2 Puerto 5432

Security group → inbound → PostgreSQL / 5432 → **My IP**.

### 9.3 Archivo `.env` (cada persona el suyo)

```text
cd RUTA\DEL\ProyectoBigData
conda activate bigdata
copy .env.example .env
notepad .env
```

Completa:

```text
AWS_HOST=tu-endpoint.xxxxx.us-east-1.rds.amazonaws.com
AWS_PORT=5432
AWS_USER=postgres
AWS_PASSWORD=tu_contraseña
AWS_DATABASE=postgres
```

`.env` está en `.gitignore`. **No lo subas.**

### 9.4 Cargar tablas

```text
python scripts/subir_resultados_aws.py --dry-run
python scripts/subir_resultados_aws.py
```

Tablas típicas: `resumen_global`, `co2_aeropuerto_mes`, `co2_aeropuerto_hora`, `rodaje_clima`, `rodaje_clima_independiente`, `escenario_ahorro`, `benchmark_dask`.

Verificación SQL:

```sql
SELECT COUNT(*) FROM resumen_global;
SELECT * FROM resumen_global ORDER BY anio;
```

Suma de `co2_t_bajo` ≈ **10.303.625**.

Si el lab se reinicia: vuelve a crear RDS, actualiza `.env` y corre otra vez `subir_resultados_aws.py`.

---

## 10. Grafana

### Opción recomendada: Grafana en Windows

1. Instala Grafana OSS: https://grafana.com/grafana/download  
2. Abre http://localhost:3000 (`admin` / `admin` la primera vez).
3. **Connections → Data sources → PostgreSQL**  
   - Host: `TU_ENDPOINT:5432`  
   - Database / user / password: los del `.env`  
   - TLS: `disable` si Academy lo permite  
4. **Save & test** (debe quedar en verde).
5. **Dashboards → Import** → sube `docs/grafana_dashboard.json`  
   o crea paneles pegando el SQL de `docs/grafana_paneles.md`.

### Etiquetas obligatorias (auditoría D4)

Si tienes estos KPI, los títulos deben ser:

| Valor | Título correcto |
|---|---|
| 41.279.609 | **Tramos de rodaje válidos (salidas + llegadas)** |
| 13,17 min | **Tiempo promedio por tramo de rodaje** |

No digas “vuelos únicos” ni “operaciones” para el 41,3 M.

### Selector de escenario

Variable `escenario` = `bajo` / `alto` (6 vs 12 kg/min). El alto es hipotético.

### Capturas

Guarda en `data/evidencia/` (o `data/evidencia/grafana/`):

- Conexión en verde  
- Tablero escenario bajo  
- Top 10 / hora / tramos / ahorro  
- Mismo KPI en escenario alto (opcional)

---

## 11. Auditoría de calidad (opcional, solo lectura)

No modifica resultados productivos:

```text
python scripts/auditar_calidad_rodaje.py
```

Salidas en `data/resultados/auditoria/`. Documentación en `docs/auditoria/`.

---

## 12. Orden recomendado en una sola tarde

| Orden | Comando / acción | Tiempo aprox. |
|---:|---|---|
| 1 | `conda activate bigdata` + `cd` al proyecto | 1 min |
| 2 | Tener `data/raw` + `data/parquet` (o Prefetch descarga) | 0–varias h |
| 3 | `python scripts/medir_volumen_entrada.py` | 1 min |
| 4 | `python scripts/calcular_co2.py` | ~15–30 s |
| 5 | Notebook EDA Run All | 1–2 min |
| 6 | Prefect server + flujo + fallo controlado | 10–15 min + capturas |
| 7 | `python scripts/benchmark_dask.py --pausa` | 10–15 min + capturas |
| 8 | AWS Lab + `.env` + `subir_resultados_aws.py` | 30–45 min |
| 9 | Grafana conectar + paneles + capturas | 30–60 min |

**AWS + Grafana:** hazlos en la misma sesión de Academy (4 h).

---

## 13. Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| `conda` no se reconoce | Usa Anaconda Prompt, no PowerShell de Cursor |
| `not a git repository` | Estás fuera de la carpeta del proyecto; haz `cd` a `ProyectoBigData` |
| No hay Parquet / ZIP | Pide la carpeta `data/` al grupo o corre Prefect para descargar |
| Pruebas de `calcular_co2.py` fallan | No “ajustes” cifras; revisa que sea el Parquet completo 2023–2025 |
| Prefect puerto ocupado | Cierra otra instancia o reinicia la Terminal 1 |
| Dask puerto 8787 ocupado | Usa el enlace que imprime el script |
| AWS no conecta | Security group puerto 5432 a tu IP; endpoint y clave en `.env` |
| Grafana Cloud no conecta | Abre 5432 temporalmente o usa Grafana local (más simple) |
| Se acabó el Lab de Academy | Recrea RDS, actualiza `.env`, vuelve a subir CSV |

---

## 14. Qué no hacer

- No subir `.env`, contraseñas ni endpoints a GitHub o al chat.
- No subir ZIP / Parquet / datos por vuelo a AWS.
- No cambiar `6` / `12` / `3.16` / `180` sin acuerdo del grupo.
- No sumar los dos escenarios de ahorro como si fueran independientes.
- No presentar el CO₂ como “medido en el avión”: es **estimación** a partir de minutos de rodaje.

---

## 15. Documentos de apoyo

| Archivo | Para qué |
|---|---|
| `README.md` | Resumen del proyecto |
| `docs/guia_aws_grafana.md` | AWS y Grafana detallado |
| `docs/grafana_paneles.md` | SQL de cada panel |
| `docs/grafana_dashboard.json` | Importar tablero |
| `docs/volumenes_por_etapa.md` | Bytes y filas por etapa |
| `docs/auditoria/` | Decisiones y calidad de datos |
| `docs/CHECKLIST_ENTREGA_FINAL.md` | Lista de entrega |
| `config.py` | Parámetros modificables |

---

## 16. Comprobación rápida “¿ya está todo?”

En Anaconda Prompt, desde la raíz del proyecto:

```text
conda activate bigdata
python scripts/medir_volumen_entrada.py
python scripts/calcular_co2.py
python scripts/subir_resultados_aws.py --dry-run
```

Si los tres terminan sin error y tienes capturas de Prefect, Dask y Grafana, el recorrido técnico está completo.
