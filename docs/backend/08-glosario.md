# 08 · Glosario

[← Volver al índice](README.md)

Los términos están en orden alfabético. Entre paréntesis se indica dónde aparecen en el proyecto.

| Término | Definición |
|---------|------------|
| **API** | *Interfaz de Programación de Aplicaciones*. Un programa que recibe peticiones y responde con datos (en JSON) en lugar de páginas. Nuestro backend es una API. |
| **`assert`** | Instrucción de Python que dice "esto debe ser verdad". Si no lo es, la prueba falla. (`test_*.py`) |
| **ASGI** | Estándar con el que un servidor (Uvicorn) se comunica con un framework de Python (FastAPI). |
| **Backend** | La parte del sistema que corre en el servidor: guarda datos y aplica reglas. Su contraparte es el *frontend*. |
| **Base64** | Forma de escribir datos binarios con letras y números. **No es cifrado**: cualquiera lo decodifica. El payload de un JWT va en base64. |
| **bcrypt** | Algoritmo para hashear contraseñas, lento a propósito y con sal. (`security.py → hashear`) |
| **Bearer** | "Portador". Tipo de autenticación en el que basta con presentar el token: `Authorization: Bearer <token>`. |
| **Cache-Control** | Encabezado HTTP que indica al navegador si puede guardar una copia de la respuesta. Usamos `no-store` (RF-06). (`main.py → sin_cache`) |
| **Ciclo vigente** | El ciclo escolar en curso o, entre ciclos, el próximo. (`services.py → ciclo_vigente`) |
| **Código de estado** | Número de tres cifras con el que el servidor resume el resultado: 200 OK, 201 creado, 401, 403, 404, 409, 422, 500. Ver [06-errores.md](06-errores.md). |
| **Commit (base de datos)** | Confirmar los cambios de una transacción para que queden guardados. (`db.commit()`) |
| **CORS** | *Cross-Origin Resource Sharing*. Regla del navegador que impide que una página de un origen llame a una API de otro, salvo que la API lo permita. (`main.py`, puerto 5500) |
| **Dependencia (`Depends`)** | Función que FastAPI ejecuta antes del endpoint para entregarle algo que necesita: una sesión de base de datos, el usuario actual. (`Depends(get_db)`, `Depends(requiere_admin)`) |
| **Endpoint** | Combinación de método HTTP + ruta que la API atiende, por ejemplo `POST /usuarios/login`. Ver [05-endpoints.md](05-endpoints.md). |
| **Entorno virtual (venv)** | Carpeta con un Python y librerías aislados para un proyecto. (`backend/venv/`) |
| **Esquema (schema)** | Clase de Pydantic que describe la forma de los datos que entran o salen y los valida. (`schemas.py`) |
| **Fixture** | Función de pytest que prepara algo para las pruebas (un cliente, datos) y que la prueba recibe como parámetro. (`conftest.py → client`) |
| **Flush** | Enviar a la base los cambios pendientes **sin confirmarlos**, por ejemplo para conocer el `id` generado antes del commit. (`services.py → registrarse`) |
| **Framework** | Conjunto de herramientas que da estructura a un programa y resuelve lo repetitivo. FastAPI es un framework web. |
| **Frontend** | La parte que ve el usuario (HTML, CSS, JS en el navegador). Consume la API. (`proyecto-escolar/frontend/`) |
| **Hash** | Resultado de una función de un solo sentido: de la contraseña sale un texto, pero no se puede regresar a la contraseña. |
| **HTTP** | Protocolo con el que el navegador y el servidor se comunican mediante peticiones y respuestas. |
| **`HTTPException`** | Excepción de FastAPI que, al lanzarse, se convierte en una respuesta con código de error y `{"detail": "..."}`. (`services.py`, `security.py`) |
| **Idempotente** | Que ejecutarlo una o varias veces da el mismo resultado. (`services.py → sembrar_catalogos`) |
| **Inyección de dependencias** | Técnica en la que una función **recibe** lo que necesita en lugar de crearlo ella misma. En FastAPI se hace con `Depends`. |
| **JSON** | Formato de texto para datos: `{"nombre": "Ana", "roles": ["estudiante"]}`. Es lo que envían y reciben frontend y backend. |
| **JWT** | *JSON Web Token*. Texto firmado que identifica una sesión; contiene `sub`, `exp` y `jti`. (`security.py → crear_token`) |
| **`jti`** | Identificador único de un JWT. Sirve para revocarlo en el logout. (`TokenRevocado`) |
| **Llave foránea (FK)** | Columna que guarda el `id` de una fila de otra tabla para relacionarlas. (`Curso.docente_id`) |
| **Llave primaria (PK)** | Columna que identifica de forma única cada fila. (`Usuario.id`) |
| **Método HTTP** | El "verbo" de una petición: `GET` consulta, `POST` crea o ejecuta, `PATCH` modifica en parte. |
| **Middleware** | Código que se ejecuta en **todas** las peticiones, antes y después del endpoint. (`CORSMiddleware`, `sin_cache`) |
| **Modelo** | Clase de SQLAlchemy que representa una tabla. (`models.py`) |
| **`monkeypatch`** | Fixture de pytest para reemplazar algo temporalmente durante una prueba, como la fecha de hoy. (`conftest.py`) |
| **Muchos a muchos** | Relación en la que un registro de A se relaciona con varios de B y viceversa. Se resuelve con una tabla intermedia. (`UsuarioRol`) |
| **OpenAPI / Swagger** | Estándar para describir una API. FastAPI lo genera solo y lo muestra en `/docs`. |
| **ORM** | *Object-Relational Mapper*. Traduce entre clases de Python y tablas de la base. SQLAlchemy es un ORM. |
| **Parámetro de consulta (query)** | Dato opcional en la URL después de `?`: `/admin/usuarios?estado=pendiente`. |
| **Parámetro de ruta (path)** | Parte variable de la URL: el `3` en `/docente/cursos/3`. |
| **`parametrize`** | Decorador de pytest que ejecuta una misma prueba con varios conjuntos de datos. |
| **Payload** | El contenido (los datos) de un JWT o de una petición. |
| **Petición / Respuesta** | Lo que envía el cliente (método, ruta, encabezados, cuerpo) y lo que regresa el servidor (código, encabezados, cuerpo). |
| **Pydantic** | Librería de validación de datos con clases y tipos. (`schemas.py`) |
| **Rollback** | Deshacer los cambios de una transacción que no se confirmó. (`db.rollback()`) |
| **Router** | Grupo de endpoints relacionados, con un prefijo común. (`routers/usuarios.py` → `/usuarios`) |
| **Sal (salt)** | Valor aleatorio que se mezcla con la contraseña antes de hashearla, para que contraseñas iguales den hashes distintos. |
| **`SECRET_KEY`** | Clave con la que se firman los JWT. Se lee de una variable de entorno. (`security.py`) |
| **Sembrar (seed)** | Llenar la base con datos iniciales: carreras, mallas, ciclo. (`services.py → sembrar_catalogos`) |
| **Serializar** | Convertir un objeto de Python a JSON para enviarlo. FastAPI lo hace usando el `response_model`. |
| **Servicio (capa de)** | Donde vive la lógica de negocio. Los routers delegan aquí. (`services.py`) |
| **Sesión de base de datos** | Conversación abierta con la base en la que se acumulan cambios hasta el commit. (`SessionLocal`, `get_db`) |
| **SQL** | Lenguaje para consultar bases de datos relacionales (`SELECT`, `INSERT`…). SQLAlchemy lo escribe por nosotros. |
| **SQLite** | Base de datos que vive en un solo archivo. (`sistema_escolar.db`) |
| **`TestClient`** | Cliente de FastAPI que hace peticiones a la app sin levantar un servidor. Usa `httpx` por dentro. (`conftest.py`) |
| **Token** | Texto que el servidor entrega al iniciar sesión y que el cliente presenta en cada petición para identificarse. |
| **Transacción** | Grupo de operaciones en la base que se guardan todas juntas o ninguna. (`registrarse`: Usuario + perfil + rol) |
| **Única (restricción)** | Regla que impide dos filas con el mismo valor en una columna o combinación. (`correoInstitucional`, `Matricula(curso_id, estudiante_id)`) |
| **Uvicorn** | Servidor que recibe las conexiones de red y se las entrega a FastAPI. (`uvicorn main:app --reload`) |
| **Validación** | Revisar que los datos cumplan las reglas (tipo, formato, longitud) antes de usarlos. |
| **Variable de entorno** | Valor configurado en el sistema o la terminal, fuera del código. (`SECRET_KEY`, `DOCENTE_REQUIERE_APROBACION`) |

[← Pruebas](07-pruebas.md) · [Volver al índice](README.md)
