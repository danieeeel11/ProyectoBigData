# Proyecto de Big Data: Análisis de Puntualidad de Vuelos Comerciales en EE.UU.
https://claude.ai/artifact/WA79L8n2F1H3m7YgQys6G1

## 📌 Descripción General

Este proyecto forma parte de una maestría en Analítica Aplicada y se centra en el análisis de puntualidad de vuelos comerciales en Estados Unidos. Utilizamos datos públicos del **BTS TranStats** (Bureau of Transportation Statistics) para identificar patrones, tendencias y factores que influyen en los atrasos aéreos.

## 🎯 Objetivo Principal

Responder preguntas críticas sobre la operación aérea:
- ¿Qué rutas, aerolíneas o franjas horarias muestran mayor probabilidad de atraso?
- ¿Cuánto se explica por origen/destino vs. la causa reportada del retraso?
- ¿Cómo pueden los analistas de operaciones aeroportuarias optimizar la asignación de tiempos de espera?

## 📊 Datos del Proyecto

- **Fuente:** BTS TranStats (Bureau of Transportation Statistics de EE.UU.)
- **Período:** 1987 - 2026
- **Volumen:** ~6-7 millones de vuelos anuales
- **Tamaño mínimo:** 1.5+ GB descomprimidos
- **Justificación:** Volumen de datos que requiere enfoque de Big Data

## 🏗️ Estructura del Proyecto

El proyecto se organiza en cinco unidades temáticas:

### Unidad 2: Ingesta Reproducible y Validación
- Desarrollo de pipeline reproducible para descargar datos
- Validación del volumen de datos procesados
- Garantía de integridad en la ingesta

### Unidad 3: Comparación de Motores
- Análisis comparativo entre diferentes enfoques:
  - **Pandas:** Framework tradicional de análisis de datos
  - **Dask/DuckDB:** Herramientas optimizadas para Big Data
- Evaluación de rendimiento y escalabilidad

### Unidad 4: Pruebas Extremas y Análisis de Límites
- Stress testing de los pipelines
- Identificación de límites operacionales
- Validación bajo condiciones extremas

### Unidad 5: Entrega Final
- Documentación completa del proyecto
- Resultados y hallazgos principales
- Recomendaciones para analistas operacionales

## 👥 Equipo

El proyecto es desarrollado por **3 personas** con roles rotativos para garantizar:
- Contribución distribuida y equitativa
- Desarrollo de múltiples competencias
- Responsabilidad compartida en el código

## 🛠️ Herramientas y Tecnologías

- **Lenguaje:** Python
- **Análisis de datos:** Pandas, Dask, DuckDB
- **Procesamiento:** Big Data tools
- **Datos:** BTS TranStats API

## 📝 Notas

Este es un proyecto académico enfocado en aplicar principios de Big Data a datos reales del transporte aéreo comercial estadounidense, con énfasis en reproducibilidad, escalabilidad y análisis comparativo de tecnologías.
