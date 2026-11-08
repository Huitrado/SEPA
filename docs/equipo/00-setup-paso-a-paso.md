# 00 · Setup de SEPA en una computadora nueva (checklist)

> Lista para instalar **todo** el proyecto en una computadora con **Windows** desde cero, hasta ver funcionando registro → login → panel → logout.
> Tiempo aproximado: 30–45 minutos. Marca cada casilla al terminarla.
> Si algo falla, busca el síntoma en [03 · Problemas comunes](03-backend-como-trabajar.md#7-problemas-comunes).

Los comandos van en **PowerShell**. Para abrirla: menú Inicio → escribe "PowerShell" → Enter. Copia cada comando tal cual.

---

## Parte A · Instalar programas (una sola vez)

- [ ] **1. Instalar Python 3.10 o más nuevo** desde https://www.python.org/downloads/
  - ⚠️ En la primera pantalla del instalador **marca "Add python.exe to PATH"** y luego *Install Now*.
- [ ] **2. Comprobar Python.** Abre una PowerShell **nueva** y ejecuta:
  ```powershell
  python --version
  ```
  Debe decir `Python 3.x.x`. Si se abre la Microsoft Store, repite el paso 1 marcando la casilla.
- [ ] **3. Instalar Git** desde https://git-scm.com/download/win (todas las opciones por defecto).
- [ ] **4. Decirle a Git quién eres** (en una PowerShell nueva):
  ```powershell
  git config --global user.name "Tu Nombre"
  git config --global user.email "tu-correo@ejemplo.com"
  ```
- [ ] **5. Instalar VS Code** desde https://code.visualstudio.com/
- [ ] **6. Instalar extensiones de VS Code** (`Ctrl + Shift + X` y busca cada nombre):
  - [ ] **Python** (Microsoft)
  - [ ] **Live Server** (Ritwick Dey)
  - [ ] **Markdown Preview Mermaid Support** (para ver los diagramas de la documentación)
  - [ ] **SQLite Viewer** (para ver la base de datos)

---

## Parte B · Descargar el proyecto (una sola vez)

- [ ] **7. Ir a la carpeta donde se guardará** (por ejemplo, Documentos):
  ```powershell
  cd $HOME\Documents
  ```
- [ ] **8. Clonar el repositorio:**
  ```powershell
  git clone https://github.com/Huitrado/SEPA.git
  cd SEPA
  ```
  Si GitHub pide iniciar sesión, usa la cuenta que tenga acceso al repositorio.
- [ ] **9. Cambiar a la rama con el backend y el frontend:**
  ```powershell
  git switch integrar-frontend
  ```
  > **Por confirmar:** cuando el equipo una los cambios a `main`, este paso será `git switch main`.

---

## Parte C · Preparar el backend (una sola vez)

- [ ] **10. Entrar a la carpeta del backend:**
  ```powershell
  cd proyecto-escolar\backend
  ```
- [ ] **11. Crear el entorno virtual (venv):**
  ```powershell
  python -m venv venv
  ```
- [ ] **12. Activarlo:**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  ✅ La línea de la terminal debe empezar con `(venv)`.
  Si sale "la ejecución de scripts está deshabilitada", ejecuta esto y repite el paso 12:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
- [ ] **13. Instalar las librerías:**
  ```powershell
  pip install -r requirements.txt
  pip install pytest httpx
  ```
  (La segunda línea es para las pruebas; `requirements.txt` todavía no las incluye.)
- [ ] **14. Correr las pruebas para confirmar que todo se instaló bien:**
  ```powershell
  pytest
  ```
  ✅ Al final debe decir **`87 passed`** (tarda alrededor de un minuto).
- [ ] **15. Generar una clave secreta** y copiar el resultado:
  ```powershell
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] **16. Guardarla en la terminal** (pega tu clave entre las comillas):
  ```powershell
  $env:SECRET_KEY = "pega-aqui-la-clave"
  ```
  Guarda la clave en un lugar seguro (no en el repositorio): la necesitarás cada vez que abras una terminal nueva.
- [ ] **17. Crear el primer administrador:**
  ```powershell
  python crear_admin.py
  ```
  - Te pide nombre, apellidos, correo, **número de empleado** (será tu código para entrar, p. ej. `A-001`) y contraseña.
  - La contraseña **no se ve** al escribir; necesita 8+ caracteres, una mayúscula, una minúscula y un número.
  - ✅ Debe decir `Administrador creado (id 1). Inicia sesión con el código A-001.`
  - Esto también crea la base de datos `sistema_escolar.db` con las carreras ICOM e INFO y el ciclo escolar actual.

---

## Parte D · Encender y probar el backend

- [ ] **18. Encender el servidor** (en la misma terminal, con `(venv)` y `SECRET_KEY` ya definidos):
  ```powershell
  uvicorn main:app --reload
  ```
  ✅ Debe decir `Uvicorn running on http://127.0.0.1:8000`. **No cierres esta terminal.**
- [ ] **19. Abrir http://127.0.0.1:8000/docs** en el navegador.
  - Abre **GET /catalogos/carreras** → *Try it out* → *Execute*.
  - ✅ Debe responder `200` con ICOM e INFO.
- [ ] **20. Probar el login de administrador en `/docs`:**
  - **POST /usuarios/login** → *Try it out* → escribe `{"codigo": "A-001", "contrasena": "TuContrasena"}` → *Execute*.
  - Copia el `access_token`, haz clic en **Authorize** (arriba a la derecha), pégalo y acepta.
  - **GET /usuarios/yo** → *Execute*. ✅ Debe responder `200` con tu perfil.

---

## Parte E · Abrir el frontend

- [ ] **21. Abrir el proyecto en VS Code.** En una PowerShell **nueva** (deja la del servidor encendida):
  ```powershell
  cd $HOME\Documents\SEPA
  code .
  ```
- [ ] **22. Abrir con Live Server:** en el explorador de VS Code, clic derecho sobre `proyecto-escolar/frontend/login.html` → **Open with Live Server**.
- [ ] **23. Revisar la dirección del navegador:** debe tener **`:5500`** (p. ej. `http://127.0.0.1:5500/proyecto-escolar/frontend/login.html`).
  ⚠️ Si es otro puerto, el backend rechazará las peticiones (error de CORS). Ver [01 · Live Server](01-frontend.md#4-cómo-abrirlo-live-server-en-el-puerto-5500).
- [ ] **24. Revisar que haya internet:** sin internet las páginas se ven sin diseño (Tailwind y las fuentes vienen de internet).

---

## Parte F · Probar el flujo completo

- [ ] **25. Registro de estudiante:** en la página, clic en **Regístrate**.
  - Pestaña **Soy estudiante**, correo que termine en `@alumnos.udg.mx`, código de **9 dígitos**, contraseña tipo `Secreto123`, elige una carrera y marca la casilla.
  - ✅ Debe aparecer "¡Cuenta creada con éxito!". (El ciclo y las carreras se llenan solos desde el backend.)
- [ ] **26. Login:** entra con el **código de 9 dígitos** (no con el correo) y la contraseña.
  - ✅ Debe abrir el panel con tu nombre, correo, código y el rol "estudiante".
- [ ] **27. Logout:** clic en **Cerrar sesión**.
  - ✅ Debe regresarte al login con el aviso "Sesión cerrada correctamente".
- [ ] **28. (Opcional) Docente pendiente:** registra un docente con correo `@academicos.udg.mx` e intenta entrar.
  - ✅ Debe decir "Tu cuenta está pendiente de aprobación por un administrador".
  - Para aprobarlo: en `/docs`, con el token de administrador, usa **PATCH /admin/usuarios/{usuario_id}/estado** con `{"estado": "activo"}`. El `id` lo ves en **GET /admin/usuarios?estado=pendiente**.
- [ ] **29. (Opcional) Ver la base de datos:** en VS Code, clic sobre `proyecto-escolar/backend/sistema_escolar.db` (con SQLite Viewer) y abre la tabla `Usuario`.

🎉 Si llegaste aquí, el proyecto está listo en esa computadora.

---

## Las siguientes veces (ya instalado)

Terminal 1, el backend:

```powershell
cd $HOME\Documents\SEPA\proyecto-escolar\backend
.\venv\Scripts\Activate.ps1
$env:SECRET_KEY = "tu-clave"
uvicorn main:app --reload
```

Después, en VS Code: clic derecho sobre `proyecto-escolar/frontend/login.html` → **Open with Live Server**.

Antes de empezar a programar, trae los cambios del equipo con `git pull` (ver [03 · Flujo de Git](03-backend-como-trabajar.md#6-flujo-de-git-del-equipo)).

---

## Para entender lo que acabas de instalar

1. [01 · Frontend](01-frontend.md)
2. [02 · El backend explicado desde cero](02-backend-como-funciona.md)
3. [03 · Cómo trabajar en el backend](03-backend-como-trabajar.md)
4. [04 · La base de datos](04-base-de-datos.md)
