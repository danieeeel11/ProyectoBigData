# Checklist Proyecto Big Data — BTS On-Time Performance
## Universidad de La Sabana — Maestría en Analítica Aplicada
**Fecha límite presentación:** 10 de octubre, 2026 (10 minutos por grupo)  
**Fecha límite entrega final:** 17 de octubre, 2026 (con retroalimentación incorporada)

---

## RESUMEN EJECUTIVO DEL ESTADO

| Punto | Descripción | Estado | Responsable | Plazo |
|-------|-------------|--------|-------------|-------|
| **1.a** | Dataset + objetivo + unidad de análisis | ✅ CERRADO | Lina | — |
| **1.b** | EDA (tipos, tendencia, distribuciones, patrones) | ✅ CERRADO | Lina | — |
| **1.c** | Análisis preliminar + información de contexto | ✅ CERRADO | Lina | — |
| **1.d** | Flujo Prefect (recurrente y escalable) | ✅ CERRADO | Lina | — |
| **1.e** | Dask (2+ configuraciones workers/memoria) | ✅ CERRADO | Lina | — |
| **1.f** | Base de datos AWS RDS (solo resultado analítico) | 🔴 BLOQUEADO | Lina | 8 de oct |
| **1.g** | Visualización Grafana (nivel gerencial) | 🔴 NO INICIADO | Lina | 8 de oct |
| **1.h** | Conclusiones del proceso | 🔴 NO INICIADO | Comp. 1 | 9 de oct |
| **1.i** | Documento APA/IEEE completo | 🔴 NO INICIADO | Comp. 2 | 9 de oct |
| **1.j** | Google Docs compartido a rodolfo.meza@gmail.com | 🔴 NO INICIADO | Lina | 9 de oct |
| **1.k** | Copiar resultados al documento | 🔴 NO INICIADO | Comp. 2 | 9 de oct |
| **1.l** | Repositorio GitHub con notebooks y scripts | 🟡 EN CURSO | Lina | 10 de oct |
| **EXTRA** | Modelo ML clasificación (Unidad 5, cierre) | 🔴 NO INICIADO | Lina | 8 de oct |

---

## PRÓXIMOS PASOS (ORDEN EXACTO Y CRONOLOGÍA)

### **HOY (4 de octubre):** Modelo ML + Confirmación AWS
- [ ] Ejecutar notebook `modelo_clasificacion_atrasos.ipynb` (Regresión Logística + Random Forest)
- [ ] Capturar tabla de comparación (exactitud, precisión, recall, F1, AUC)
- [ ] Capturar lista de variables más importantes (Random Forest)
- [ ] **DECISIÓN FINAL:** AWS Academy Learner Lab vs. cuenta personal
  - Si Academy Lab: confirmar que se harán ambas sesiones (8-9 oct y 16-17 oct)
  - Si cuenta personal: crear cuenta y verificar que RDS está funcional

### **5-6 de octubre:** AWS + Grafana (Sesión única de 4h)
**Bloque dedicado:** reserva 4h contínuas sin interrupciones
1. [ ] Abrir AWS Academy Learner Lab
2. [ ] Crear instancia RDS PostgreSQL (mismo flujo que Bases de Datos)
3. [ ] Ejecutar `subir_resultados_aws.py` para cargar tablas:
   - `resumen_atrasos` (resumen_atrasos_por_aerolinea_mes.csv)
   - `benchmark_dask` (benchmark_dask.csv)
4. [ ] Verificar conexión con DuckDB/PostgreSQL
5. [ ] Crear cuenta gratuita en **Grafana Cloud** (https://grafana.com/products/cloud/)
6. [ ] Conectar RDS como fuente de datos en Grafana
7. [ ] Crear **3-4 paneles** con hallazgos principales:
   - Panel 1: % de atrasos por aerolínea (gráfico de barras)
   - Panel 2: % de atrasos por hora del día (línea)
   - Panel 3: Lluvia fuerte vs. atrasos (comparación)
   - Panel 4 (opcional): Benchmark Dask (tabla de resultados)
8. [ ] **CAPTURAR EVIDENCIA:** antes de que termine la sesión:
   - Pantallazos del dashboard de Grafana (cada panel)
   - Pantallazos de la conexión RDS exitosa (en Grafana)
   - Pantallazos de las tablas creadas en PostgreSQL (SQL)
9. [ ] Guardar capturas en `data/resultados/evidencia_aws_grafana/`
10. [ ] Guardar URL del dashboard de Grafana (si Grafana permite link público)

### **7 de octubre:** Compilación de Conclusiones + Modelo
1. [ ] Escribir conclusiones (punto 1.h) respondiendo:
   - ¿Qué predice un atraso? Resumen de hallazgos principales
   - "La lluvia fuerte casi duplica el riesgo de atraso (33.84% vs. 18.57%)"
   - "La franja horaria 18-21h tiene 3x más atrasos que las 5-8h"
   - "Según el modelo Random Forest, [variable más importante] es el factor determinante"
   - Limitaciones honestas: "El modelo no usa pronóstico de clima (solo histórico), no incluye tráfico aéreo real-time"
2. [ ] Finalizar notebook del modelo ML con **guardado** de modelo:
   ```python
   import joblib
   joblib.dump(modelo_bosque, "data/resultados/modelo_atrasos.pkl")
   ```

### **8-9 de octubre:** Documento colaborativo (Google Docs)
**Estructura recomendada (reparte secciones entre los 3):**

**Sección 1: Resumen Ejecutivo** (200-300 palabras)
- Pregunta de negocio: ¿qué causa atrasos en vuelos comerciales?
- Respuesta rápida con números (lluvia fuerte, hora del día)
- Dataset: 21M vuelos, 9.47 GB, 2023-2025

**Sección 2: Objetivo, Metodología y Unidad de Análisis** (500-700 palabras)
- Objetivo: predecir ArrDel15 (atraso ≥15 min)
- Metodología: CRISP-DM (negocio → entendimiento → preparación → modelado → evaluación → despliegue)
- Unidad de análisis: vuelo individual (date, hora, aerolínea, ruta)
- Fases ejecutadas: EDA, Pipeline ETL, Benchmark, Enriquecimiento, Modelado

**Sección 3: Exploración de Datos (EDA)** (con gráficas)
- Distribución de variable objetivo (79% a tiempo / 21% atrasados)
- Patrones por hora del día (gráfica de línea)
- Patrones por día de la semana
- Top aerolíneas por volumen y % de atrasos
- Tipos de datos, nulos, medidas de tendencia

**Sección 4: Pipeline ETL con Prefect**
- Descripción del flujo (descarga → validación → almacenamiento → recálculo)
- Captura del dashboard de Prefect Server mostrando corridas
- Volumen de entrada vs. salida (9.47 GB → 665 MB)
- Justificación: compresión columnar sin pérdida de datos

**Sección 5: Benchmark con Dask**
- Tabla de comparación: Config A (2 workers, 2 hilos, 2GB) vs. Config B (4 workers, 1 hilo, 1GB)
- Resultado: Config A fue más rápida (6.6s vs. 12.9s)
- Interpretación: menos procesos con más hilos gana en este escenario por overhead de coordinación

**Sección 6: Enriquecimiento con Clima (Open-Meteo)**
- Dataset: 20 aeropuertos, 2023-2025, clima diario
- Hallazgo: lluvia fuerte (>5mm) → 33.84% atrasos vs. 18.57% sin lluvia
- Conclusión: clima es factor contextual relevante, candidato a feature en versión mejorada del modelo

**Sección 7: Modelo de Clasificación**
- Descripción: Regresión Logística vs. Random Forest
- Tabla de métricas (exactitud, precisión, recall, F1, AUC)
- Variables más importantes (del Random Forest)
- Matriz de confusión y reporte de clasificación

**Sección 8: Base de Datos AWS + Visualización Grafana**
- Proceso: instancia RDS PostgreSQL → tablas (`resumen_atrasos`, `benchmark_dask`) → Grafana Cloud
- Paneles creados (descripción + capturas)
- URL del dashboard (si es público)

**Sección 9: Conclusiones**
- Respuesta a la pregunta original ¿qué causa atrasos?
- Hallazgos más fuertes (con números exactos)
- Limitaciones del estudio
- Líneas de trabajo futuro (clima como feature real, tráfico aéreo real-time, análisis causal)

**Sección 10: Referencias**
- BTS TranStats (https://www.transtats.bts.gov)
- Open-Meteo API
- Librerías: scikit-learn, dask, prefect, pandas, duckdb, sqlalchemy
- Normas APA/IEEE para citas

---

## PARÁMETROS POR REQUISITO DEL DOCENTE

### **1.a: Identificar dataset, objetivo, unidad de análisis**
✅ **Cumple:**
- Dataset: Bureau of Transportation Statistics (BTS) On-Time Performance, 1987-presente
- Volumen: 9.47 GB descomprimido (36 archivos mensuales, 2023-2025)
- Objetivo: predecir si un vuelo llegará con ≥15 minutos de atraso (ArrDel15)
- Unidad: vuelo individual (identidad única: FlightDate + Reporting_Airline + Flight_Num)
- Usuario: Analista de Operaciones de Aerolínea (toma decisiones sobre scheduling, asignación de recursos)

### **1.b: EDA — analítica descriptiva, tipos, tendencia, distribuciones, patrones, variable objetivo y features**
✅ **Cumple:**
- Tipos de datos: categóricas (Airline, Origin, Dest, DayOfWeek, Month) + numéricas (ArrDelay, DepDelay, Distance, CRSDepTime)
- Tendencia central: ArrDelay media 7.4 min (mediana -6.0), DepDelay media 12.8, Distance media 837 millas
- Distribuciones: ArrDel15 desbalanceada (21.23% atrasados vs. 78.77% a tiempo)
- Patrones: atrasos suben de 8.9% (5am) a 30.7% (20h); domingo 23.9% vs. martes 17.9%; por aerolínea rango 14.87%-29.28%
- Variable objetivo: ArrDel15 (1=atraso ≥15 min, 0=a tiempo)
- Features candidatas: Reporting_Airline, Origin, Dest, DayOfWeek, Month, CRSDepTime (→ franja horaria), Distance

### **1.c: Análisis preliminar e información adicional de contexto**
✅ **Cumple:**
- Identificación de fuga de datos: columnas de causa (`CarrierDelay`, `WeatherDelay`, etc.) **no deben usarse** como features (solo se conocen post-hecho)
- Información contextual adicionada: clima diario (Open-Meteo) para 20 aeropuertos principales
  - Lluvia fuerte (>5mm) → 33.84% atrasos vs. 18.57% sin lluvia (+15.27 pp)
  - Viento fuerte (≥40 km/h) → 34.77% atrasos vs. 22.75% normal (+12.02 pp)
- Conclusión: no se requiere información adicional obligatoria para el modelo actual; clima es candidato a mejora futura

### **1.d: Flujo Prefect recurrente y escalable**
✅ **Cumple:**
- Script: `scripts/flujo_ingesta_prefect.py`
- Tareas: descargar_mes, validar_y_convertir, recalcular_analitica
- Idempotente: si lo vuelves a correr, omite meses ya descargados
- Escalable: cambiar lista de periodos en el código reutiliza todo el pipeline
- Evidencia: dashboard de Prefect Server (localhost:4200) muestra flujos ejecutados
- Volumen entrada: 9.47 GB → salida (Parquet particionado): 665 MB, 20.928.579 filas

### **1.e: Dask con 2+ configuraciones de workers y memoria**
✅ **Cumple:**
- Script: `scripts/benchmark_dask.py`
- Config A: 2 workers × 2 hilos/worker, 2GB memoria/worker → **6.6 segundos**
- Config B: 4 workers × 1 hilo/worker, 1GB memoria/worker → 12.9 segundos
- Tarea: agregación groupby(Year, Month, Reporting_Airline) sobre 665 MB Parquet
- Hallazgo: Config A gana porque menos overhead de coordinación entre procesos en dataset pequeño
- Evidencia: tabla CSV (`data/resultados/benchmark_dask.csv`) + capturas del dashboard Dask

### **1.f: Base de datos AWS con SOLO resultado analítico (NO datos crudos)**
🔴 **Por hacer:**
- Tecnología: AWS RDS PostgreSQL (usando AWS Academy Learner Lab)
- Tablas a cargar:
  - `resumen_atrasos` (528 filas: year, month, airline, % atrasados)
  - `benchmark_dask` (2 filas: comparación de configuraciones)
- Script: `scripts/subir_resultados_aws.py` (credenciales en `.env`, gitignored)
- Validación: query SELECT en PostgreSQL confirma datos cargados
- Documentación: captura de pantalla de tablas creadas

### **1.g: Visualización Grafana (nivel gerencial)**
🔴 **Por hacer:**
- Plataforma: Grafana Cloud (gratuito, https://grafana.com/products/cloud/)
- Fuente: RDS PostgreSQL creada en (1.f)
- Paneles (mínimo 3, máximo 5):
  1. **Atrasos por aerolínea** (gráfico de barras horizontal, ordenado descendente)
  2. **Atrasos por hora del día** (línea con picos identificados)
  3. **Atrasos vs. lluvia** (comparación 2 barras: sin lluvia vs. lluvia fuerte)
  4. (Opcional) Benchmark Dask (tabla o card)
  5. (Opcional) Atrasos por día de la semana
- Estilo: colores corporativos, etiquetas claras, unidades explícitas (%)
- Acceso: URL compartible (si Grafana permite) o capturas de pantalla
- Audiencia: gerente de operaciones de aerolínea (no técnico)

### **1.h: Conclusiones del proceso**
🔴 **Por hacer:**
- Responder: ¿qué causa atrasos? ¿Qué aprendimos del Big Data?
- Incluir números exactos de hallazgos clave (5-7 bullets)
- Mencionar modelo ML y qué variable es más predictiva
- Limitaciones honestas (2-3 puntos)
- Líneas de trabajo futuro (2-3 puntos)
- Extensión: 500-700 palabras

### **1.i: Documento APA/IEEE completo**
🔴 **Por hacer:**
- Formato: Google Docs (colaborativo) o Word docx (convertir a PDF para envío final)
- Normas: 
  - APA: encabezados numerados, citas autor-año, tabla de contenidos, referencias al final
  - IEEE: pie de página para citas, figura/tabla numeradas, referencias numeradas
- Estructura: resumen + 10 secciones (ver más arriba)
- Extensión estimada: 15-25 páginas (con gráficas, capturas)
- Revisión: cada integrante lee al menos 1 sección ajena

### **1.j: Documento Google Docs compartido**
🔴 **Por hacer:**
- Crear Google Doc con título descriptivo
- Compartir con `rodolfo.meza@gmail.com` con permiso **EDITOR** (no solo comentario/lector)
- Verificar acceso (pedirle que abra el link)
- No compartir con enlace público (seleccionar "Personas específicas")

### **1.k: Copiar resultados de análisis al documento**
🔴 **Por hacer:**
- Copiar/pegar en cada sección:
  - Tablas de métricas (EDA, modelo, Dask)
  - Gráficas (histogramas, líneas de atrasos por hora)
  - Capturas de pantalla (Prefect dashboard, Grafana panels, PostgreSQL tablas)
  - Comandos SQL o Python ejecutados (en apéndice)

### **1.l: Repositorio GitHub**
🟡 **En curso:**
- Repositorio: privado, colaboradores confirmados
- Estructura actual:
  ```
  /notebooks
    - unidad2_ingesta_bts.ipynb
    - unidad2b_eda_bts.ipynb
    - analisis_clima_atrasos.ipynb
    - modelo_clasificacion_atrasos.ipynb
  /scripts
    - flujo_ingesta_prefect.py
    - medir_volumen_entrada.py
    - descargar_clima_openmeteo.py
    - benchmark_dask.py
    - subir_resultados_aws.py
  /data
    - raw/          (ZIP descargados, NO en git)
    - parquet/      (Parquet particionado, NO en git)
    - clima/        (CSV del clima, pequeño, SÍ en git)
    - resultados/   (CSVs analíticos + evidencia_aws_grafana/, SÍ en git)
  .gitignore        (data/raw/, data/parquet/, *.zip, .env)
  README.md         (descripción general, cómo correr)
  ```
- Por hacer:
  - [ ] Agregar notebook del modelo ML
  - [ ] Crear README.md con orden de ejecución
  - [ ] Verificar que .gitignore excluya datos pesados
  - [ ] Commits finales antes del 10 de octubre

---

## RÚBRICA DEL DOCENTE (12 puntos, ponderación estimada)

| # | Criterio | Puntos | Cómo se verifica | Estado |
|----|----------|--------|------------------|--------|
| 1.a | Dataset > 1.5GB + objetivo + unidad | 5 | Contrato + documento | ✅ |
| 1.b | EDA (tipos, tendencia, distribuciones) | 10 | Notebook + gráficas | ✅ |
| 1.c | Análisis preliminar + contexto | 5 | Notebook clima + conclusiones | ✅ |
| 1.d | Prefect (recurrente, escalable) | 10 | Dashboard Prefect + 2 corridas | 🔴 (falta captura 2ª corrida) |
| 1.e | Dask (2+ configs, benchmark) | 10 | Tabla comparativa + dashboard | ✅ |
| 1.f | AWS (resultado analítico, no crudo) | 10 | Screenshot RDS tablas | 🔴 |
| 1.g | Grafana (hallazgos gerenciales) | 10 | Captura paneles + URL | 🔴 |
| 1.h | Conclusiones | 5 | Sección del documento | 🔴 |
| 1.i | Documento APA/IEEE | 10 | Documento compilado | 🔴 |
| 1.j | Compartir con docente | 3 | Link aceptado + permisos | 🔴 |
| 1.k | Copiar resultados al documento | 5 | Documento con datos integrados | 🔴 |
| 1.l | GitHub con notebooks + scripts | 7 | Repo público/accesible | 🟡 |
| **EXTRA** | Modelo ML (cierre Unidad 5) | +5 | 2 modelos comparados | 🔴 |
| | **TOTAL** | **95 (+5)** | | **~40%** |

---

## FECHAS CRÍTICAS Y BLOCKERS

| Fecha | Acción | Blocker | Mitiga |
|-------|--------|---------|--------|
| 4 oct | Modelo ML | Ninguno (depende solo de Parquet local) | Ejecutar hoy |
| 5-6 oct | AWS + Grafana sesión 4h | AWS Academy reinicia cada 4h | Hacer TODO en 1 sesión; capturar evidencia antes del reinicio |
| 7 oct | Conclusiones + compile | Esperar a Grafana | Ya tener paneles listos |
| 8-9 oct | Documento Google | Comp. 2 escribiendo | Empezar estructura hoy, rellenar en paralelo |
| 9 oct 23:59 | Compartir con rodolfo.meza@gmail.com | Link roto / permisos | Verificar acceso de tercero |
| 10 oct 10:00 | Presentación (10 min) | Nervios | Slide con resumen ejecutivo preescrito |
| 17 oct 23:59 | Entrega final con retroalimentación | Conflictos de merge en docs | Usar historia de versiones de Google Docs |

---

## CONVERSIÓN A PROMPT PARA LINA (ORDEN DE TRABAJO)

```
PROMPT: Construir puntos 1.f–1.l del proyecto de Big Data

Contexto:
- Proyecto grupal: predecir atrasos de vuelos (BTS On-Time Performance)
- Metodología: CRISP-DM (negocio, EDA, preparación, modelado, evaluación, despliegue)
- Dataset: 21M vuelos (9.47 GB entrada, 665 MB Parquet resultado)
- Equipo: 3 personas (Lina = ML + AWS/Grafana, Comp1 = conclusiones, Comp2 = documento)
- Plazo: 10 de octubre presentación (10 min), 17 de octubre entrega final

Próximos pasos inmediatos (en orden):
1. Ejecutar modelo_clasificacion_atrasos.ipynb (2 modelos: Regresión Logística + Random Forest)
2. Capturar tabla de comparación (exactitud, recall, F1, AUC) y variables importantes
3. Sesión dedicada 4h: AWS Academy Lab → RDS PostgreSQL → subir_resultados_aws.py → Grafana Cloud → 3-4 paneles → capturar evidencia
4. Escribir conclusiones (punto h)
5. Crear Google Doc, distribuir secciones entre los 3
6. Compilar documento con gráficas, capturas, tablas
7. Verificar GitHub con README.md
8. Ensayar presentación (10 minutos, resumen ejecutivo)

Métricas de éxito:
- Documento con normas APA/IEEE ✓
- Grafana con 3+ paneles de hallazgos gerenciales ✓
- Modelo ML con comparación de 2 algoritmos ✓
- AWS con tablas de resultado (sin datos crudos) ✓
- Presentación ensayada y grabada (backup si falla la viva)
- GitHub actualizado con orden de ejecución (README.md) ✓
```

---

## DUDAS FRECUENTES RESUELTAS

**P: ¿Trabajar sobre Parquet (665 MB) incumple el requisito de 1.5 GB?**  
**R:** NO. El requisito de 1.5 GB aplica al **conjunto de datos de entrada** (9.47 GB descomprimido, descargado de BTS). El Parquet es el *resultado de la transformación* (punto 1.d), una mejor representación para análisis, no una muestra reducida. Es estándar en Big Data: procesar datos masivos pero almacenar solo agregados. El punto 1.f del docente lo confirma: "SOLO DEBEN SUBIR A AWS EL RESULTADO DE LA ANALÍTICA, NO EL CONJUNTO DE DATOS ORIGINAL."

**P: ¿Debo guardar los ZIP/CSV originales para demostrar que trabajé con 9.47 GB?**  
**R:** NO. Con la medición que ya hicieron (`medir_volumen_entrada.py`), queda documentado: "1.05 GB ZIP, 9.47 GB descomprimido". Eso es suficiente para la rúbrica. Los ZIP/CSV pueden borrarse después (ocupan espacio innecesario).

**P: ¿El modelo ML es obligatorio o extra?**  
**R:** Es el "cierre natural" de la Unidad 5 (fue el objetivo original del proyecto). Sin él, el punto 1.h (conclusiones) queda débil. Recomendación: hacerlo, suma 5 puntos bonus y responde bien a la pregunta "¿para qué se usa todo esto?"

**P: ¿Puedo usar AWS personal en lugar de Academy Lab?**  
**R:** Sí, pero va a costar ~$2-3 USD durante todo el proyecto (db.t3.micro a ~$0.016/h, muy barato). Academy Lab es gratis pero requiere recriar todo cada 4h. Decisión tuya según riesgo vs. costo.

---

## SIGUIENTE PASO: CONFIRMAR Y AVANZAR
- [ ] Confirmar decision AWS (Academy Lab = confirmado, personal = crear cuenta hoy)
- [ ] Ejecutar modelo ML (hoy si es posible)
- [ ] Agendar bloque 4h para AWS + Grafana (5-6 de octubre)
- [ ] Repartir secciones del documento entre los 3 del grupo
- [ ] Actualizar este checklist cuando algo se complete

