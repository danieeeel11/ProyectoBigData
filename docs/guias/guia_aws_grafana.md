# Cómo subir los resultados a AWS y verlos en Grafana

Esta guía es para alguien que lo hace por primera vez. Hay que hacerla de una sola vez si usas AWS Academy Learner Lab: la sesión dura unas 4 horas y al cerrarla la base se borra. Por eso el script se puede volver a correr y deja las tablas otra vez.

Lo que se sube son tablas ya resumidas (miles de filas). No se sube el Parquet ni los ZIP.

## 1. Crear la base en AWS Academy

1. Entra a AWS Academy y abre **Learner Lab**. Pulsa **Start Lab**. Espera a que el círculo quede verde.
2. Pulsa **AWS**, que abre la consola.
3. Arriba a la derecha, región **us-east-1** (N. Virginia), salvo que el laboratorio te obligue a otra.
4. Busca el servicio **RDS**.
5. **Create database**.
6. Elige **PostgreSQL**. Plantilla **Free tier** si aparece; si no, **Dev/Test**.
7. Estos valores:
   - Identificador: `rodaje-co2`
   - Usuario maestro: `postgres` (anótalo; va en `.env` como `AWS_USER`)
   - Contraseña: invéntala y guárdala solo en tu `.env`. No la pegues en el chat ni en el código.
   - Clase de instancia: **db.t3.micro**
   - Almacenamiento: 20 GB está bien
   - Acceso público: **Yes**
   - Grupo de seguridad: crea uno nuevo. Más abajo hay que abrir el puerto.
8. Crea la base y espera a que el estado diga **Available** (10–15 minutos). No cierres el laboratorio.
9. Entra a la base y copia el **Endpoint**. Se parece a `rodaje-co2.xxxxx.us-east-1.rds.amazonaws.com`. Ese texto es `AWS_HOST`. No lo subas a GitHub.

## 2. Abrir el puerto 5432 solo para tu IP

1. En la ficha de la base, abre el **VPC security group**.
2. **Edit inbound rules** → **Add rule**.
3. Tipo: **PostgreSQL**. Puerto: **5432**. Origen: **My IP**.
4. Guarda.

Si más adelante usas Grafana Cloud (está fuera de tu casa), tendrás que abrir el puerto un rato a la IP de Grafana y **cerrarlo al terminar**. Es más simple y más seguro instalar Grafana en Windows y conectarte a la base desde tu misma IP. Esta guía recomienda esa opción.

## 3. Llenar el archivo .env

En Anaconda Prompt, parado en la carpeta del proyecto:

```
conda activate bigdata
copy .env.example .env
```

Abre `.env` con el bloc de notas y completa:

```
AWS_HOST=el-endpoint-que-copiaste
AWS_PORT=5432
AWS_USER=postgres
AWS_PASSWORD=la-que-inventaste
AWS_DATABASE=postgres
```

`.env` ya está en `.gitignore`. Comprueba que GitHub Desktop no lo muestre para subir.

## 4. Probar sin conectarte, y luego cargar

```
python scripts/subir_resultados_aws.py --dry-run
python scripts/subir_resultados_aws.py
```

El dry-run solo revisa que existan los CSV. El segundo comando crea o reemplaza estas tablas:

| Tabla | Qué es | Filas, más o menos |
|---|---|---|
| `resumen_global` | CO2 por año | 3 |
| `co2_aeropuerto_mes` | aeropuerto, año y mes | unos miles |
| `co2_aeropuerto_hora` | aeropuerto y hora de salida | unos miles |
| `rodaje_clima` | clima, una etiqueta por vuelo | 5 |
| `rodaje_clima_independiente` | lluvia, nieve y viento por separado | 6 |
| `escenario_ahorro` | bajar 10 % y bajar hasta la mediana | 2 |
| `benchmark_dask` | tiempos de Dask | 2 o 3 |

`benchmark_dask` solo aparece si ya corriste `python scripts/benchmark_dask.py`. Si el dry-run dice que falta, corre primero el benchmark o acepta que esa tabla se omita: el script salta los CSV que no existen, pero el dry-run avisa.

## 5. Comprobar con SQL

En RDS → tu base → **Query Editor** (o con DBeaver / pgAdmin), conectado con el mismo usuario:

```sql
SELECT COUNT(*) FROM resumen_global;
SELECT COUNT(*) FROM co2_aeropuerto_mes;
SELECT COUNT(*) FROM co2_aeropuerto_hora;
SELECT * FROM resumen_global ORDER BY anio;
```

Tienes que ver 3 años y un total de escenario bajo cercano a **10.303.625 toneladas**.

## 6. Capturas de esta parte

Tómalas antes de que se acabe el laboratorio:

1. La base en RDS con estado Available y el endpoint visible (tapa la contraseña si sale).
2. La regla de entrada del puerto 5432 limitada a tu IP.
3. El resultado de los `SELECT COUNT(*)`.
4. El contenido de `resumen_global`.

## 7. Grafana en Windows (opción recomendada)

1. Descarga Grafana OSS para Windows desde https://grafana.com/grafana/download
2. Instálalo y abre http://localhost:3000
3. Usuario y clave iniciales: `admin` / `admin`. Te pide cambiarla. Esa clave es local; no va al proyecto.
4. **Connections → Data sources → Add data source → PostgreSQL**.
5. Host: el endpoint de RDS y el puerto, así: `tu-endpoint:5432`
6. Database: `postgres`. User y password: los del `.env`. TLS: `disable`, salvo que RDS te exija otra cosa.
7. **Save & test**. Tiene que decir que la conexión funciona.
8. **Dashboards → New → Import**. Sube el archivo `docs/grafana_dashboard.json`.
9. Cuando pregunte la fuente de datos, elige el PostgreSQL que acabas de crear.
10. Si algún panel queda vacío, abre el panel, pega la consulta de `docs/grafana_paneles.md` y guarda.

Arriba del tablero hay un selector **escenario** (bajo o alto). Bajo es 6 kg/min. Alto es 12 kg/min y en el informe debe decir **por validar**.

## 8. Si usas Grafana Cloud en lugar de Grafana local

Solo si no puedes instalar Grafana. Es menos seguro, porque la base queda alcanzable desde internet durante la conexión.

1. Crea una cuenta en https://grafana.com/products/cloud/
2. En el grupo de seguridad de RDS, abre el 5432 a la IP que te indique Grafana (o, en el peor caso, a `0.0.0.0/0` **solo mientras armas los paneles**).
3. Crea el data source igual que arriba.
4. Importa el JSON.
5. **Cuando termines las capturas, borra esa regla de entrada.** Si se acaba el laboratorio, la base desaparece igual; aun así, ciérrala.

## 9. Capturas de Grafana

1. Conexión del data source en verde.
2. El tablero completo en escenario bajo.
3. El top 10 de aeropuertos.
4. El mapa o las líneas por hora.
5. El panel de ahorro.
6. El mismo KPI cambiado a escenario alto, para mostrar que el ranking no cambia de forma y solo se duplica el CO2.
