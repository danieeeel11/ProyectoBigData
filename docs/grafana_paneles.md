# Paneles de Grafana para Sostenibilidad

La audiencia no necesita ver SQL. Cada panel responde una pregunta. Las consultas se pegan en el modo **Code** del panel, con formato **Table**.

Antes, crea una variable del tablero:

- Nombre: `escenario`
- Tipo: Custom
- Valores: `bajo,alto`
- Etiqueta visible: `Escenario de consumo`

`bajo` = 6 kg de combustible por minuto. `alto` = 12 kg/min, **por validar**.

El CO2 del escenario alto es el doble del bajo. El orden de los aeropuertos no cambia, porque todos se multiplican por el mismo número.

## 1. KPI — toneladas de CO2

- Tipo: **Stat**
- Título: `CO2 del rodaje en tierra, 2023-2025`
- Unidad: toneladas (`suffix` t, o unidad personalizada)
- Consulta:

```sql
SELECT
  CASE
    WHEN '$escenario' = 'alto' THEN ROUND(SUM(co2_t_alto))
    ELSE ROUND(SUM(co2_t_bajo))
  END AS toneladas
FROM resumen_global;
```

En escenario bajo el número tiene que verse como **10.303.625**.

Al lado, un panel **Bar chart** o **Time series** no hace falta: con tres años basta un gráfico de barras.

- Tipo: **Bar chart**
- Título: `CO2 por año`
- Eje X: `anio`. Eje Y: `toneladas`. Unidad: t.

```sql
SELECT
  anio,
  CASE
    WHEN '$escenario' = 'alto' THEN ROUND(co2_t_alto)
    ELSE ROUND(co2_t_bajo)
  END AS toneladas
FROM resumen_global
ORDER BY anio;
```

## 2. Top 10 aeropuertos

- Tipo: **Bar chart**, orientación horizontal
- Título: `Aeropuertos con más CO2 de rodaje de salida`
- Consulta (salida nada más: TaxiOut en el origen):

```sql
SELECT
  aeropuerto,
  CASE
    WHEN '$escenario' = 'alto' THEN ROUND(SUM(co2_t_alto_salida))
    ELSE ROUND(SUM(co2_t_bajo_salida))
  END AS co2_salida_t
FROM co2_aeropuerto_mes
GROUP BY aeropuerto
ORDER BY co2_salida_t DESC
LIMIT 10;
```

Orden esperado en escenario bajo: ORD, DFW, DEN, ATL, CLT, LGA, SEA, LAX, LAS, JFK. ORD cerca de **392.002 t**.

## 3. CO2 por hora del día

- Tipo: **Bar chart** (todo el sistema) y, si quieres el detalle, **Heatmap** de los 10 aeropuertos de arriba
- Título: `CO2 de salida según la hora programada`
- La hora ya viene corregida: 0 a 23. El valor 2400 de BTS está en la hora 0. No existe un grupo 24.

```sql
SELECT
  hora,
  CASE
    WHEN '$escenario' = 'alto' THEN ROUND(SUM(co2_t_alto) / 1000, 1)
    ELSE ROUND(SUM(co2_t_bajo) / 1000, 1)
  END AS miles_de_toneladas
FROM co2_aeropuerto_hora
GROUP BY hora
ORDER BY hora;
```

El pico está en las **8** (unas 516 mil toneladas en escenario bajo), luego las **7** y las **6**. La tarde repunta hacia las **17–18**, pero menos que la mañana.

Mapa de calor (hora × aeropuerto), solo el top 10:

```sql
SELECT
  hora,
  aeropuerto,
  ROUND(SUM(co2_t_bajo), 1) AS co2_t
FROM co2_aeropuerto_hora
WHERE aeropuerto IN ('ORD', 'DFW', 'DEN', 'ATL', 'CLT', 'LGA', 'SEA', 'LAX', 'LAS', 'JFK')
GROUP BY hora, aeropuerto
ORDER BY hora, aeropuerto;
```

En el heatmap: eje X = `hora`, eje Y = `aeropuerto`, color = `co2_t`.

## 4. Aeropuertos con el rodaje más lento

- Tipo: **Bar chart** horizontal
- Título: `Minutos promedio de rodaje de salida (aeropuertos con más de 50.000 vuelos)`
- Unidad del eje: minutos

```sql
SELECT
  aeropuerto,
  ROUND(SUM(min_rodaje_salida) / NULLIF(SUM(vuelos_salida), 0), 1) AS minutos_promedio,
  SUM(vuelos_salida) AS vuelos
FROM co2_aeropuerto_mes
GROUP BY aeropuerto
HAVING SUM(vuelos_salida) > 50000
ORDER BY minutos_promedio DESC
LIMIT 10;
```

Los primeros son JFK (27,0), EWR (24,6), LGA (24,2) y ORD (24,2). ORD sale en los dos rankings: mucho volumen y, además, un rodaje lento.

## 5. Escenario de ahorro

- Tipo: **Table** o dos **Stat**
- Título: `CO2 que se evitaría en el escenario bajo`

```sql
SELECT
  concepto,
  detalle,
  ROUND(co2_t_bajo_actual) AS co2_actual_t,
  ROUND(co2_t_evitado) AS co2_evitado_t,
  ROUND(co2_t_bajo_escenario) AS co2_si_se_logra_t
FROM escenario_ahorro;
```

Lectura, ya calculada con los datos completos:

- Bajar el rodaje un **10 %** evita cerca de **1.030.363 t**.
- Llevar la salida de los aeropuertos lentos hasta la mediana de los aeropuertos grandes (**15,7 min**) evita cerca de **1.007.869 t**. Esa cuenta es solo de salida; no promete bajar también la llegada.

## 6. Clima (opcional)

- Tipo: **Bar chart**
- Título: `Minutos de rodaje de salida según el clima del día`

Usa la comparación independiente (cada fenómeno por su lado):

```sql
SELECT condicion, vuelos, min_promedio_salida
FROM rodaje_clima_independiente
ORDER BY min_promedio_salida DESC;
```

La nieve está en **26,4 min** y un día sin nieve en **19,7 min**. Lluvia fuerte: **22,7** frente a **18,9** sin lluvia. Viento de 40 km/h o más: **22,3** frente a **20,0**. El clima es diario y solo cubre 20 aeropuertos de origen; no es la causa única del rodaje.
