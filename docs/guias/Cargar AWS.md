# **AWS y Grafana, en una sola sesión**

Sigue `docs/guia_aws_grafana.md` sin saltarte pasos. En resumen:

Start Lab en AWS Academy.
Crea RDS PostgreSQL (`db.t3.micro`, acceso público).
Abre el puerto 5432 solo a tu IP.
Copia el endpoint.
En la carpeta del proyecto: `copy .env.example .env` y llena host, usuario y clave. No los pegues en el chat ni en el código.
Corre:

`python scripts/subir_resultados_aws.py --dry-run`

`python scripts/subir_resultados_aws.py`

En la base, comprueba:

`SELECT COUNT(*) FROM resumen_global;
SELECT * FROM resumen_global ORDER BY anio;`

El escenario bajo, sumando los tres años, debe verse como **10.303.625** toneladas.

**Instala Grafana en Windows/Mac/Linux**, conéctalo a esa base y sube `docs/grafana_dashboard.json`. Si un panel queda vacío, pega la consulta de `docs/grafana_paneles.md`.

Captura la base, los conteos, la conexión en verde y el tablero en escenario bajo y en alto.
**Hazlo antes de que se acabe el laboratorio de 4 horas. Si se cierra, se puede volver a cargar con el mismo script.**
