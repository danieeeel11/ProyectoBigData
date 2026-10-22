# Guía Práctica de Git: Flujo de Trabajo con Ramas

Esta guía explica paso a paso los comandos más utilizados para trabajar con ramas en Git, actualizar cambios y mantener sincronizado tu repositorio.

---

## 1. Cambiar de rama o crear una nueva

### Ver en qué rama estás actualmente
```bash
git branch
```

### Crear y cambiarte a una nueva rama
```bash
git checkout -b nombre-de-tu-rama
```
*(O en versiones más recientes de Git: `git switch -c nombre-de-tu-rama`)*

### Cambiarte a una rama existente
```bash
git checkout nombre-de-tu-rama
```
*(O en versiones más recientes de Git: `git switch nombre-de-tu-rama`)*

---

## 2. Guardar y subir cambios a tu rama local/remota

Cuando realizas modificaciones en tu código y quieres guardarlas en tu rama:

1. **Revisar el estado de los archivos:**
   ```bash
   git status
   ```

2. **Añadir los archivos modificados al área de preparación (staging):**
   ```bash
   git add .
   ```

3. **Crear el commit con un mensaje descriptivo:**
   ```bash
   git commit -m "Descripción de los cambios realizados"
   ```

4. **Enviar los cambios a GitHub/GitLab (Servidor remoto):**
   ```bash
   git push origin nombre-de-tu-rama
   ```
   *Nota: Si es la primera vez que subes esa rama, usa:*
   ```bash
   git push -u origin nombre-de-tu-rama
   ```

---

## 3. Traer los cambios de la rama `main` a tu rama actual

Para asegurarte de que tu rama tenga las últimas actualizaciones de la rama principal (`main`):

1. **Asegúrate de estar en tu rama de trabajo:**
   ```bash
   git checkout nombre-de-tu-rama
   ```

2. **Traer la información actualizada del servidor:**
   ```bash
   git fetch origin
   ```

3. **Fusionar los cambios de `main` dentro de tu rama:**
   ```bash
   git merge origin/main
   ```
   *(Si hay conflictos de código, resuélvelos en tu editor, guarda, ejecuta `git add .` y luego `git commit`).*

---

## 4. Actualizar la rama `main` con los ajustes de tu rama

Cuando hayas terminado tu trabajo y quieras integrar tus cambios en la rama principal (`main`):

### Opción A: Desde la Terminal (Local)

1. **Guarda y sube todos tus cambios en tu rama actual.**
2. **Cámbiate a la rama `main`:**
   ```bash
   git checkout main
   ```
3. **Asegúrate de que tu `main` local esté actualizado con el remoto:**
   ```bash
   git pull origin main
   ```
4. **Fusiona tu rama en `main`:**
   ```bash
   git merge nombre-de-tu-rama
   ```
5. **Sube los cambios actualizados de `main` a GitHub/GitLab:**
   ```bash
   git push origin main
   ```

### Opción B: Mediante Pull Request (Recomendado para trabajo en equipo)

1. Sube tu rama con `git push origin nombre-de-tu-rama`.
2. Ve a la plataforma web de GitHub / GitLab.
3. Haz clic en **"Compare & pull request"**.
4. Revisa los cambios y confirma la fusión (**Merge pull request**).

---

## 5. Crear una rama de respaldo (Backup)

Si deseas hacer una copia de respaldo de la rama `main` tal como está en el servidor:

```bash
git fetch origin
git branch backup origin/main
```
Para subir también el respaldo al servidor remoto:
```bash
git push origin backup
```

---

## 6. Comandos útiles de consulta

* **Ver el historial de commits recientes:**
  ```bash
  git log --oneline -n 5
  ```
* **Ver qué correo y usuario están configurados en Git:**
  ```bash
  git config user.name
  git config user.email
  ```