"""Lógica de negocio. Los routers solo reciben, delegan aquí y responden."""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from config import (ASISTENCIA_EXTRAORDINARIO, ASISTENCIA_ORDINARIO, CARPETA_ARCHIVOS,
                    CARRERAS_INICIALES, DESEMPENO_ALERTA, DIAS_SEMANA, DOCENTE_REQUIERE_APROBACION,
                    ESTADOS_ASISTENCIA, ESTADOS_QUE_CUENTAN, EXTENSIONES_PERMITIDAS, ORDEN_SEMAFORO,
                    PRIORIDAD_PANEL, SEMAFORO_AMARILLO, SEMAFORO_CALIFICACION_VERDE, SEMAFORO_VERDE,
                    TAMANO_MAXIMO_ARCHIVO, UMBRAL_APROBATORIO, rol_por_correo)
from security import crear_token, hashear, verificar

import json
from pathlib import Path

_PLANES = Path(__file__).with_name("planes.json")

# Se verifica contra este hash cuando el código no existe, para que tardar lo mismo
# no delate qué códigos están registrados.
_HASH_FALSO = hashear("contrasena-falsa")

def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")

# ======================================================================
# Ciclos escolares: el estado sale de las fechas, no de un valor guardado
# ======================================================================
def hoy() -> date:  # las pruebas lo reemplazan para fijar la fecha
    return date.today()

def estado_ciclo(ciclo: models.CicloEscolar) -> str:
    """'proximo' si aún no inicia, 'activo' si está en curso, 'cerrado' si ya terminó."""
    h = hoy()
    if h < date.fromisoformat(ciclo.fechaInicio):
        return "proximo"
    if h > date.fromisoformat(ciclo.fechaTermino):
        return "cerrado"
    return "activo"

def _ciclo_dict(c: models.CicloEscolar) -> dict:
    return {"id": c.id, "nombreOficial": c.nombreOficial, "fechaInicio": c.fechaInicio,
            "fechaTermino": c.fechaTermino, "estado": estado_ciclo(c)}

def listar_ciclos(db: Session, estado: str | None = None) -> list[dict]:
    ciclos = [_ciclo_dict(c) for c in db.query(models.CicloEscolar).order_by(models.CicloEscolar.id.desc())]
    return [c for c in ciclos if estado is None or c["estado"] == estado]

def ciclo_vigente(db: Session) -> models.CicloEscolar | None:
    """El ciclo en curso; entre dos ciclos (del 17 de dic al 15 de ene) es el que sigue."""
    ciclos = db.query(models.CicloEscolar).all()
    en_curso = [c for c in ciclos if estado_ciclo(c) == "activo"]
    if en_curso:
        return en_curso[0]
    proximos = sorted((c for c in ciclos if estado_ciclo(c) == "proximo"), key=lambda c: c.fechaInicio)
    return proximos[0] if proximos else None

def ciclo_para_fecha(f: date) -> tuple[str, date, date]:
    """Nombre y fechas oficiales del ciclo en curso; entre ciclos (17 dic a 15 ene), el siguiente."""
    a = f.year + 1 if f > date(f.year, 12, 16) else f.year
    if f < date(a, 7, 16):
        return f"{a}-A", date(a, 1, 16), date(a, 7, 15)
    return f"{a}-B", date(a, 7, 16), date(a, 12, 16)

# ======================================================================
# Catálogos (RF-02)
# ======================================================================
def sembrar_catalogos(db: Session) -> None:
    if db.query(models.Carrera).count() == 0:
        for clave, nombre in CARRERAS_INICIALES.items():
            db.add(models.Carrera(clave=clave, nombre=nombre))
        db.commit()
    if db.query(models.Materia).count() == 0:
        _sembrar_planes(db)
    if db.query(models.CicloEscolar).count() == 0:
        nombre, inicio, fin = ciclo_para_fecha(hoy())
        ciclo = models.CicloEscolar(nombreOficial=nombre, fechaInicio=inicio.isoformat(),
                                    fechaTermino=fin.isoformat(), estado="")
        ciclo.estado = estado_ciclo(ciclo)  # informativo, igual que en crearCiclo
        db.add(ciclo)
        db.commit()

def _sembrar_planes(db: Session) -> None:
    """Crea MallaCurricular, Materia y MallaMateria a partir de planes.json."""
    planes = json.loads(_PLANES.read_text(encoding="utf-8"))
    materias: dict[str, models.Materia] = {}
    for carrera, plan in planes.items():
        malla = models.MallaCurricular(carrera=carrera, generacion=plan["generacion"],
                                       nombrePlan=plan["nombrePlan"])
        db.add(malla)
        db.flush()
        for m in plan["materias"]:
            materia = materias.get(m["clave"])
            if materia is None:  # materia compartida entre carreras: se crea una sola vez
                materia = models.Materia(clave=m["clave"], nombre=m["nombre"])
                db.add(materia)
                db.flush()
                materias[m["clave"]] = materia
            db.add(models.MallaMateria(semestreBase=m["semestre"],
                                       mallaCurricular_id=malla.id, materia_id=materia.id))
    db.commit()

# RF-94: el administrador da de alta y mantiene el catálogo de materias
def _clave_libre(db: Session, clave: str, materia_id: int | None = None) -> None:
    otra = db.query(models.Materia).filter_by(clave=clave).first()
    if otra and otra.id != materia_id:
        raise HTTPException(409, "Ya existe una materia con esa clave")

def _materia(db: Session, materia_id: int) -> models.Materia:
    materia = db.get(models.Materia, materia_id)
    if not materia:
        raise HTTPException(404, "Materia no encontrada")
    return materia

def crear_materia(db: Session, datos: schemas.MateriaCrear) -> models.Materia:
    _clave_libre(db, datos.clave)
    materia = models.Materia(clave=datos.clave, nombre=datos.nombre)
    db.add(materia)
    db.commit()
    db.refresh(materia)
    return materia

def actualizar_materia(db: Session, materia_id: int, datos: schemas.MateriaActualizar) -> models.Materia:
    materia = _materia(db, materia_id)
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    if "clave" in cambios:
        _clave_libre(db, cambios["clave"], materia.id)
    for campo, valor in cambios.items():
        setattr(materia, campo, valor)
    db.commit()
    db.refresh(materia)
    return materia

def eliminar_materia(db: Session, materia_id: int) -> None:
    """Solo si nadie la usa: un plan de estudios, un curso o un historial académico."""
    materia = _materia(db, materia_id)
    for tabla in (models.MallaMateria, models.Curso, models.HistorialAcademico):
        if db.query(tabla).filter_by(materia_id=materia.id).first():
            raise HTTPException(409, "No se puede eliminar una materia que ya se usa en un plan de "
                                     "estudios, un curso o un historial académico")
    db.delete(materia)
    db.commit()

def crear_carrera(db: Session, datos: schemas.CarreraCrear) -> models.Carrera:
    if db.query(models.Carrera).filter(
            or_(models.Carrera.clave == datos.clave, models.Carrera.nombre == datos.nombre)).first():
        raise HTTPException(409, "Ya existe una carrera con esa clave o nombre")
    carrera = models.Carrera(clave=datos.clave, nombre=datos.nombre)
    db.add(carrera)
    db.commit()
    db.refresh(carrera)
    return carrera

def _validar_catalogos(db: Session, datos: schemas.UsuarioCrear) -> None:
    if not db.query(models.Carrera).filter_by(clave=datos.carrera).first():
        raise HTTPException(422, "La carrera seleccionada no pertenece al catálogo oficial")
    vigente = ciclo_vigente(db)  # el ciclo del estudiante es el que está en curso
    if not vigente:
        raise HTTPException(409, "No hay un ciclo escolar en curso registrado; contacta a un administrador")
    if datos.ciclo != vigente.nombreOficial:
        raise HTTPException(422, f"El ciclo en curso es {vigente.nombreOficial}")

# ======================================================================
# Registro, sesión y perfil (RF-01 a RF-07, RF-89 a RF-92)
# ======================================================================
def _roles_de(db: Session, usuario_id: int) -> list[str]:
    filas = (db.query(models.Rol.nombre).select_from(models.usuario_rol)
             .join(models.Rol, models.Rol.id == models.usuario_rol.c.rol_id)
             .filter(models.usuario_rol.c.usuario_id == usuario_id).all())
    return [f[0] for f in filas]

def _panel_de(roles: list[str]) -> str | None:
    return next((r for r in PRIORIDAD_PANEL if r in roles), None)

def _codigo_de(db: Session, usuario_id: int) -> str | None:
    estudiante = db.get(models.Estudiante, usuario_id)
    if estudiante:
        return estudiante.codigoEstudiante
    for perfil in (models.Docente, models.Administrador):
        fila = db.get(perfil, usuario_id)
        if fila:
            return fila.noEmpleado
    return None

def registrarse(db: Session, datos: schemas.UsuarioCrear) -> models.Usuario:
    """Registro público. El rol sale del dominio del correo (el esquema ya garantizó que es válido)."""
    rol_nombre = rol_por_correo(datos.correoInstitucional)
    if db.query(models.Usuario).filter_by(correoInstitucional=datos.correoInstitucional).first():
        raise HTTPException(409, "El correo institucional ya está registrado")

    if rol_nombre == "estudiante":
        if db.query(models.Estudiante).filter_by(codigoEstudiante=datos.codigo).first():
            raise HTTPException(409, "El código de estudiante ya está registrado")
        _validar_catalogos(db, datos)
        estado = "activo"
    else:
        if db.query(models.Docente).filter_by(noEmpleado=datos.noEmpleado).first():
            raise HTTPException(409, "El número de empleado ya está registrado")
        estado = "pendiente" if DOCENTE_REQUIERE_APROBACION else "activo"

    rol = db.query(models.Rol).filter_by(nombre=rol_nombre).first() or models.Rol(nombre=rol_nombre)
    usuario = models.Usuario(
        nombre=datos.nombre, apellidos=datos.apellidos,
        correoInstitucional=datos.correoInstitucional,
        contrasena=hashear(datos.contrasena),
        estado=estado, fechaRegistro=_ahora(),
    )
    try:  # Usuario + perfil + Rol: todo o nada
        db.add_all([usuario, rol])
        db.flush()
        if rol_nombre == "estudiante":
            db.add(models.Estudiante(id=usuario.id, codigoEstudiante=datos.codigo,
                                     carrera=datos.carrera, ciclo=datos.ciclo))
        else:
            db.add(models.Docente(id=usuario.id, noEmpleado=datos.noEmpleado,
                                  departamento=datos.departamento))
        db.execute(models.usuario_rol.insert().values(usuario_id=usuario.id, rol_id=rol.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe un registro con esos datos")
    db.refresh(usuario)
    return usuario

def _ids_por_codigo(db: Session, codigo: str) -> set[int]:
    """El 'código' de acceso es el código de estudiante o el número de empleado."""
    consultas = (
        db.query(models.Estudiante.id).filter(models.Estudiante.codigoEstudiante == codigo),
        db.query(models.Docente.id).filter(models.Docente.noEmpleado == codigo),
        db.query(models.Administrador.id).filter(models.Administrador.noEmpleado == codigo),
    )
    return {fila[0] for q in consultas for fila in q}

def iniciarSesion(db: Session, cred: schemas.UsuarioLogin) -> dict:
    usuarios = [db.get(models.Usuario, i) for i in _ids_por_codigo(db, cred.codigo)]
    if not usuarios:
        verificar(cred.contrasena, _HASH_FALSO)
    u = next((x for x in usuarios if x and verificar(cred.contrasena, x.contrasena)), None)
    if not u:  # mismo mensaje para código inexistente y contraseña errónea
        raise HTTPException(401, "Código o contraseña incorrectos")
    if u.estado == "pendiente":  # solo se revela con la contraseña correcta
        raise HTTPException(403, "Tu cuenta está pendiente de aprobación por un administrador")
    if u.estado != "activo":
        raise HTTPException(403, "Tu cuenta está desactivada")
    roles = _roles_de(db, u.id)
    return {"access_token": crear_token(u.id), "token_type": "bearer", "roles": roles,
            "panel": _panel_de(roles), "nombre": f"{u.nombre} {u.apellidos}"}

def cerrarSesion(db: Session, payload: dict) -> None:
    """RF-06 / RF-91: el token deja de servir aunque no haya expirado."""
    jti = payload["jti"]
    if not db.get(models.TokenRevocado, jti):
        expira = datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat()
        db.add(models.TokenRevocado(jti=jti, expira=expira))
    # limpieza: un token expirado ya es inválido por sí solo
    db.query(models.TokenRevocado).filter(
        models.TokenRevocado.expira < datetime.now(timezone.utc).isoformat()).delete()
    db.commit()

def perfil_de(db: Session, usuario: models.Usuario) -> dict:
    roles = _roles_de(db, usuario.id)
    return {"id": usuario.id, "nombre": usuario.nombre, "apellidos": usuario.apellidos,
            "correoInstitucional": usuario.correoInstitucional, "codigo": _codigo_de(db, usuario.id),
            "roles": roles, "panel": _panel_de(roles)}

# ======================================================================
# Administración (RF-08, RF-93)
# ======================================================================
def _usuario_admin(db: Session, u: models.Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "apellidos": u.apellidos,
            "correoInstitucional": u.correoInstitucional, "estado": u.estado,
            "roles": _roles_de(db, u.id)}

def _crear_personal(db: Session, datos, rol_nombre: str, perfil, extra: dict) -> models.Usuario:
    """Crea Usuario + perfil (Docente/Administrador) + rol, todo en una transacción."""
    if db.query(models.Usuario).filter_by(correoInstitucional=datos.correoInstitucional).first():
        raise HTTPException(409, "El correo institucional ya está registrado")
    if db.query(perfil).filter_by(noEmpleado=datos.noEmpleado).first():
        raise HTTPException(409, "El número de empleado ya está registrado")

    rol = db.query(models.Rol).filter_by(nombre=rol_nombre).first() or models.Rol(nombre=rol_nombre)
    usuario = models.Usuario(
        nombre=datos.nombre, apellidos=datos.apellidos,
        correoInstitucional=datos.correoInstitucional,
        contrasena=hashear(datos.contrasena),
        estado="activo", fechaRegistro=_ahora(),
    )
    try:
        db.add_all([usuario, rol])
        db.flush()
        db.add(perfil(id=usuario.id, noEmpleado=datos.noEmpleado, **extra))
        db.execute(models.usuario_rol.insert().values(usuario_id=usuario.id, rol_id=rol.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe un registro con esos datos")
    db.refresh(usuario)
    return usuario

def crear_docente(db: Session, datos: schemas.DocenteCrear) -> models.Usuario:
    return _crear_personal(db, datos, "docente", models.Docente, {"departamento": datos.departamento})

def crear_administrador(db: Session, datos: schemas.AdminCrear) -> models.Usuario:
    return _crear_personal(db, datos, "administrador", models.Administrador, {})

def listar_usuarios(db: Session, rol: str | None = None, estado: str | None = None) -> list[dict]:
    q = db.query(models.Usuario)
    if estado:
        q = q.filter(models.Usuario.estado == estado)
    if rol:
        q = (q.join(models.usuario_rol, models.usuario_rol.c.usuario_id == models.Usuario.id)
              .join(models.Rol, models.Rol.id == models.usuario_rol.c.rol_id)
              .filter(models.Rol.nombre == rol))
    return [_usuario_admin(db, u) for u in q.order_by(models.Usuario.id).all()]

def cambiar_estado_usuario(db: Session, admin: models.Usuario, usuario_id: int, estado: str) -> dict:
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(404, "Usuario no encontrado")
    if usuario.id == admin.id:
        raise HTTPException(409, "No puedes cambiar tu propio estado")  # evita quedarse sin admins
    usuario.estado = estado
    db.commit()
    return _usuario_admin(db, usuario)

def recuperarContrasena(db: Session, usuario_id: int, nueva: str) -> None:
    """RF-07: restablecimiento manual que solicita el usuario a su coordinador o administrador."""
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(404, "Usuario no encontrado")
    usuario.contrasena = hashear(nueva)
    db.commit()

def crearCiclo(db: Session, datos: schemas.CicloCrear) -> dict:
    if db.query(models.CicloEscolar).filter_by(nombreOficial=datos.nombreOficial).first():
        raise HTTPException(409, "Ya existe un ciclo con ese nombre")
    ciclo = models.CicloEscolar(
        nombreOficial=datos.nombreOficial,
        fechaInicio=datos.fechaInicio.isoformat(),
        fechaTermino=datos.fechaTermino.isoformat(),
        estado="",
    )
    ciclo.estado = estado_ciclo(ciclo)  # informativo: el estado real siempre se calcula con las fechas
    db.add(ciclo)
    db.commit()
    db.refresh(ciclo)
    return _ciclo_dict(ciclo)

def reasignar_docente(db: Session, curso_id: int, docente_id: int) -> models.Curso:
    curso = db.get(models.Curso, curso_id)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")
    docente = db.get(models.Docente, docente_id)
    if not docente:
        raise HTTPException(404, "Docente no encontrado")
    if db.get(models.Usuario, docente_id).estado != "activo":
        raise HTTPException(409, "El docente está inactivo")
    curso.docente_id = docente_id
    db.commit()
    db.refresh(curso)
    return curso

# ======================================================================
# Gestión académica: cursos (RF-09 a RF-18, RF-95)
# ======================================================================
def _umbral_para(tipo: str) -> float:
    """RF-18: 60 fijo para 'numerica'. En Aprobado/No Aprobado no aplica umbral (se guarda 0)."""
    return UMBRAL_APROBATORIO if tipo == "numerica" else 0.0

def generarCodigoUnico() -> str:
    return uuid.uuid4().hex[:8].upper()

def _dias_a_texto(dias: list[str]) -> str:
    return ",".join(d for d in DIAS_SEMANA if d in dias)  # en orden de la semana

def crearCurso(db: Session, docente: models.Usuario, datos: schemas.CursoCrear) -> models.Curso:
    ciclo = db.get(models.CicloEscolar, datos.cicloEscolar_id)
    if not ciclo:  # RF-09
        raise HTTPException(404, "Ciclo escolar no encontrado")
    if estado_ciclo(ciclo) == "cerrado":
        raise HTTPException(409, "No se pueden crear cursos en un ciclo que ya terminó")
    if db.query(models.Curso).filter_by(docente_id=docente.id, nombreMateria=datos.nombreMateria,
                                        seccion=datos.seccion, cicloEscolar_id=ciclo.id).first():
        raise HTTPException(409, "Ya tienes un curso con esa materia y sección en este ciclo")

    for _ in range(5):  # RF-14: reintenta si el código aleatorio choca con otro
        curso = models.Curso(
            nombreMateria=datos.nombreMateria, seccion=datos.seccion, descripcion=datos.descripcion,
            tipoEvaluacion=datos.tipoEvaluacion, umbralNumerico=_umbral_para(datos.tipoEvaluacion),
            diasSemana=_dias_a_texto(datos.diasSemana),
            horaInicio=datos.horaInicio.strftime("%H:%M"), horaFin=datos.horaFin.strftime("%H:%M"),
            cicloEscolar_id=ciclo.id, codigoCurso=generarCodigoUnico(),
            estado="activo", docente_id=docente.id,
        )
        db.add(curso)
        try:
            db.commit()
            db.refresh(curso)
            return curso
        except IntegrityError:
            db.rollback()
    raise HTTPException(500, "No se pudo generar un código de curso único")

def _curso_del_docente(db: Session, docente: models.Usuario, curso_id: int) -> models.Curso:
    """RF-95: solo el docente creador del curso accede a sus controles."""
    curso = db.get(models.Curso, curso_id)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")
    if curso.docente_id != docente.id:
        raise HTTPException(403, "Este curso no te pertenece")
    return curso

def cursos_del_docente(db: Session, docente: models.Usuario, estado: str = "activo") -> list[models.Curso]:
    """RF-11: por defecto solo los activos; los archivados se piden con estado='archivado'."""
    return (db.query(models.Curso).filter_by(docente_id=docente.id, estado=estado)
            .order_by(models.Curso.id).all())

def alumnos_de_curso(db: Session, docente: models.Usuario, curso_id: int) -> list[dict]:
    curso = _curso_del_docente(db, docente, curso_id)
    filas = (db.query(models.Matricula, models.Estudiante, models.Usuario)
             .select_from(models.Matricula)
             .join(models.Estudiante, models.Estudiante.id == models.Matricula.estudiante_id)
             .join(models.Usuario, models.Usuario.id == models.Estudiante.id)
             .filter(models.Matricula.curso_id == curso.id)
             .order_by(models.Usuario.apellidos, models.Usuario.nombre).all())
    return [{
        "matricula_id": m.id, "estudiante_id": e.id, "codigoEstudiante": e.codigoEstudiante,
        "nombre": u.nombre, "apellidos": u.apellidos, "correoInstitucional": u.correoInstitucional,
        "estado": m.estado, "fechaInscripcion": m.fechaInscripcion,
        "calificacionAcumuladaActual": m.calificacionAcumuladaActual,
    } for m, e, u in filas]

def actualizar_curso(db: Session, docente: models.Usuario, curso_id: int,
                     datos: schemas.CursoActualizar) -> models.Curso:
    curso = _curso_del_docente(db, docente, curso_id)
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    if "diasSemana" in cambios:
        cambios["diasSemana"] = _dias_a_texto(cambios["diasSemana"])
    for campo in ("horaInicio", "horaFin"):
        if campo in cambios:
            cambios[campo] = cambios[campo].strftime("%H:%M")
    if "tipoEvaluacion" in cambios:
        cambios["umbralNumerico"] = _umbral_para(cambios["tipoEvaluacion"])
    if cambios.get("horaFin", curso.horaFin) <= cambios.get("horaInicio", curso.horaInicio):
        raise HTTPException(422, "La hora de fin debe ser posterior a la hora de inicio")
    for campo, valor in cambios.items():
        setattr(curso, campo, valor)
    db.commit()
    db.refresh(curso)
    return curso

def cambiar_estado_curso(db: Session, docente: models.Usuario, curso_id: int, estado: str) -> models.Curso:
    curso = _curso_del_docente(db, docente, curso_id)  # RF-10
    curso.estado = estado
    db.commit()
    db.refresh(curso)
    return curso

# ======================================================================
# Inscripciones (RF-15)
# ======================================================================
def inscribirseCurso(db: Session, usuario: models.Usuario, codigo_curso: str) -> models.Curso:
    estudiante = db.get(models.Estudiante, usuario.id)
    if not estudiante:
        raise HTTPException(403, "Solo los estudiantes pueden inscribirse")
    curso = db.query(models.Curso).filter_by(codigoCurso=codigo_curso).first()
    if not curso:
        raise HTTPException(404, "El código no corresponde a ningún curso")
    if curso.estado != "activo":
        raise HTTPException(409, "El curso no está activo")
    if db.query(models.Matricula).filter_by(curso_id=curso.id, estudiante_id=estudiante.id).first():
        raise HTTPException(409, "Ya estás inscrito en este curso")

    db.add(models.Matricula(curso_id=curso.id, estudiante_id=estudiante.id,
                            fechaInscripcion=_ahora(), estado="activo"))
    try:
        db.commit()
    except IntegrityError:  # doble clic simultáneo: lo frena el UniqueConstraint
        db.rollback()
        raise HTTPException(409, "Ya estás inscrito en este curso")
    return curso

# ======================================================================
# Control de asistencia (RF-19 a RF-28, RF-49)
# ======================================================================
_DIAS_CON_DOMINGO = (*DIAS_SEMANA, "domingo")  # date.weekday(): 0 = lunes ... 6 = domingo

def calcular_porcentaje_asistencia(estados: list[str]) -> float:
    """(asistencias + retardos) / sesiones guardadas × 100. `estados` son los de las sesiones
    con listaGuardada; sin sesiones guardadas el alumno va al 100 %."""
    contadas = [e for e in estados if e in ESTADOS_ASISTENCIA]
    if not contadas:
        return 100.0
    return sum(e in ESTADOS_QUE_CUENTAN for e in contadas) * 100 / len(contadas)

def estatus_normativo(porcentaje: float) -> str:
    """RF-49: Ordinario >= 80 %, Extraordinario >= 65 % y < 80 %, Sin Derecho < 65 %."""
    if porcentaje >= ASISTENCIA_ORDINARIO:
        return "Ordinario"
    if porcentaje >= ASISTENCIA_EXTRAORDINARIO:
        return "Extraordinario"
    return "Sin Derecho"

def semaforo_asistencia(porcentaje: float) -> str:
    """Verde > 85 %, amarillo de 80 % a 85 %, rojo < 80 %."""
    if porcentaje > SEMAFORO_VERDE:
        return "verde"
    if porcentaje >= SEMAFORO_AMARILLO:
        return "amarillo"
    return "rojo"

def porcentaje_asistencia(db: Session, matricula_id: int) -> float:
    """Porcentaje de un alumno en su curso, contando solo las listas guardadas."""
    estados = (db.query(models.Asistencia.estado)
               .join(models.SesionClase, models.SesionClase.id == models.Asistencia.sesionClase_id)
               .filter(models.Asistencia.matricula_id == matricula_id,
                       models.SesionClase.listaGuardada == 1).all())
    return calcular_porcentaje_asistencia([e for (e,) in estados])

def _alumnos_activos(db: Session, curso_id: int) -> list[tuple]:
    """(Matricula, Estudiante, Usuario) de las matrículas activas, por apellidos y nombre."""
    return (db.query(models.Matricula, models.Estudiante, models.Usuario)
            .select_from(models.Matricula)
            .join(models.Estudiante, models.Estudiante.id == models.Matricula.estudiante_id)
            .join(models.Usuario, models.Usuario.id == models.Estudiante.id)
            .filter(models.Matricula.curso_id == curso_id, models.Matricula.estado == "activo")
            .order_by(models.Usuario.apellidos, models.Usuario.nombre).all())

def _datos_alumno(m: models.Matricula, e: models.Estudiante, u: models.Usuario) -> dict:
    return {"matricula_id": m.id, "estudiante_id": e.id, "codigoEstudiante": e.codigoEstudiante,
            "nombre": u.nombre, "apellidos": u.apellidos}

def _sesion_del_curso(db: Session, docente: models.Usuario, curso_id: int,
                      sesion_id: int) -> models.SesionClase:
    curso = _curso_del_docente(db, docente, curso_id)
    sesion = db.get(models.SesionClase, sesion_id)
    if not sesion or sesion.curso_id != curso.id:
        raise HTTPException(404, "Sesión no encontrada")
    return sesion

def _detalle_sesion(db: Session, sesion: models.SesionClase) -> dict:
    registros = {a.matricula_id: a for a in
                 db.query(models.Asistencia).filter_by(sesionClase_id=sesion.id).all()}
    alumnos = []
    for m, e, u in _alumnos_activos(db, sesion.curso_id):
        a = registros.get(m.id)
        alumnos.append({**_datos_alumno(m, e, u), "estado": a.estado if a else "pendiente",
                        "observaciones": a.observaciones if a else None})
    return {**schemas.SesionClaseSalida.model_validate(sesion).model_dump(), "alumnos": alumnos}

def generarSesionClase(db: Session, docente: models.Usuario, curso_id: int,
                       datos: schemas.SesionClaseCrear | None) -> dict:
    """RF-19, RF-27: solo la sesión de hoy, en un día de clase del curso y sin duplicados."""
    curso = _curso_del_docente(db, docente, curso_id)
    if curso.estado != "activo":
        raise HTTPException(409, "El curso está archivado")
    ciclo = db.get(models.CicloEscolar, curso.cicloEscolar_id)
    if not ciclo or estado_ciclo(ciclo) != "activo":
        raise HTTPException(409, "El ciclo escolar del curso no está en curso")
    fecha = hoy()
    if _DIAS_CON_DOMINGO[fecha.weekday()] not in curso.diasSemana.split(","):
        raise HTTPException(409, "Hoy no es día de clase de este curso")
    if db.query(models.SesionClase).filter_by(curso_id=curso.id, fecha=fecha.isoformat()).first():
        raise HTTPException(409, "Ya existe una sesión de este curso para hoy")

    sesion = models.SesionClase(curso_id=curso.id, fecha=fecha.isoformat(), horaInicio=curso.horaInicio,
                                horaFin=curso.horaFin, tema=datos.tema if datos else None,
                                listaGuardada=0)
    db.add(sesion)
    db.flush()
    # RF-22: cada alumno activo arranca en "pendiente" hasta que se guarde la lista
    db.add_all(models.Asistencia(sesionClase_id=sesion.id, matricula_id=m.id, estado="pendiente")
               for m, _, _ in _alumnos_activos(db, curso.id))
    db.commit()
    db.refresh(sesion)
    return _detalle_sesion(db, sesion)

def ver_sesion(db: Session, docente: models.Usuario, curso_id: int, sesion_id: int) -> dict:
    return _detalle_sesion(db, _sesion_del_curso(db, docente, curso_id, sesion_id))

def guardarListaAsistencia(db: Session, docente: models.Usuario, curso_id: int, sesion_id: int,
                           datos: schemas.ListaAsistencia) -> dict:
    """RF-20, RF-23 y RF-25 (también sirve para corregir la lista de una sesión pasada)."""
    sesion = _sesion_del_curso(db, docente, curso_id, sesion_id)
    activas = {m.id for m, _, _ in _alumnos_activos(db, sesion.curso_id)}
    registros = {a.matricula_id: a for a in
                 db.query(models.Asistencia).filter_by(sesionClase_id=sesion.id).all()}
    enviadas = {a.matricula_id for a in datos.asistencias}

    ajenas = enviadas - activas
    if ajenas:
        raise HTTPException(422, "Hay alumnos que no pertenecen a este curso o no están activos "
                                 f"(matrícula {', '.join(map(str, sorted(ajenas)))})")
    faltantes = (activas & registros.keys()) - enviadas
    if faltantes:
        raise HTTPException(422, "Falta el estado de algunos alumnos de la lista "
                                 f"(matrícula {', '.join(map(str, sorted(faltantes)))})")

    for a in datos.asistencias:
        registro = registros.get(a.matricula_id)
        if not registro:  # se inscribió después de generar la sesión
            registro = models.Asistencia(sesionClase_id=sesion.id, matricula_id=a.matricula_id)
            db.add(registro)
        registro.estado = a.estado
        registro.observaciones = a.observaciones
    sesion.listaGuardada = 1
    db.commit()
    db.refresh(sesion)
    return _detalle_sesion(db, sesion)

def cuadricula_asistencia(db: Session, docente: models.Usuario, curso_id: int) -> dict:
    """RF-24, RF-26: columnas = sesiones por fecha; filas = alumnos activos con su porcentaje."""
    curso = _curso_del_docente(db, docente, curso_id)
    sesiones = (db.query(models.SesionClase).filter_by(curso_id=curso.id)
                .order_by(models.SesionClase.fecha, models.SesionClase.id).all())
    registros = {(a.matricula_id, a.sesionClase_id): a for a in
                 db.query(models.Asistencia)
                 .filter(models.Asistencia.sesionClase_id.in_([s.id for s in sesiones])).all()}
    alumnos = []
    for m, e, u in _alumnos_activos(db, curso.id):
        estados, guardados = [], []
        for s in sesiones:
            a = registros.get((m.id, s.id))
            estados.append({"sesion_id": s.id, "estado": a.estado if a else None,
                            "observaciones": a.observaciones if a else None})
            if a and s.listaGuardada:
                guardados.append(a.estado)
        porcentaje = calcular_porcentaje_asistencia(guardados)
        alumnos.append({**_datos_alumno(m, e, u), "estados": estados,
                        "porcentajeAsistencia": round(porcentaje, 2),
                        "estatusNormativo": estatus_normativo(porcentaje),
                        "semaforo": semaforo_asistencia(porcentaje)})
    return {"curso_id": curso.id, "alumnos": alumnos,
            "sesiones": [schemas.SesionClaseSalida.model_validate(s).model_dump() for s in sesiones]}

# ======================================================================
# Categorías de evaluación (RF-31, RF-32)
# ======================================================================
def _pct(valor: float) -> str:
    return f"{round(valor, 2):g}"

def _resumen_pesos(db: Session, curso_id: int) -> dict:
    """RF-32: la suma debe ser exactamente 100; si no, se guarda igual pero se advierte."""
    suma = round(sum(c.porcentajePeso for c in
                     db.query(models.CategoriaEvaluacion).filter_by(curso_id=curso_id).all()), 2)
    completos = suma == 100
    return {"sumaPesos": suma, "pesosCompletos": completos,
            "advertencia": None if completos else
            f"Los pesos de las categorías suman {_pct(suma)} %; deben sumar exactamente 100 %"}

def _validar_categoria(db: Session, curso_id: int, nombre: str, peso: float,
                       categoria_id: int | None = None) -> None:
    otras = (db.query(models.CategoriaEvaluacion).filter_by(curso_id=curso_id)
             .filter(models.CategoriaEvaluacion.id != categoria_id).all())
    if any(c.nombre.lower() == nombre.lower() for c in otras):
        raise HTTPException(409, "Ya existe una categoría con ese nombre en este curso")
    suma_otras = sum(c.porcentajePeso for c in otras)
    if round(suma_otras + peso, 2) > 100:
        raise HTTPException(409, "La suma de los pesos no puede superar 100 % "
                                 f"(las demás categorías suman {_pct(suma_otras)} %)")

def _categoria_del_curso(db: Session, docente: models.Usuario, curso_id: int,
                         categoria_id: int) -> models.CategoriaEvaluacion:
    curso = _curso_del_docente(db, docente, curso_id)
    categoria = db.get(models.CategoriaEvaluacion, categoria_id)
    if not categoria or categoria.curso_id != curso.id:
        raise HTTPException(404, "Categoría no encontrada")
    return categoria

def listar_categorias(db: Session, docente: models.Usuario, curso_id: int) -> dict:
    curso = _curso_del_docente(db, docente, curso_id)
    categorias = (db.query(models.CategoriaEvaluacion).filter_by(curso_id=curso.id)
                  .order_by(models.CategoriaEvaluacion.id).all())
    return {"categorias": categorias, **_resumen_pesos(db, curso.id)}

def crearCategoria(db: Session, docente: models.Usuario, curso_id: int,
                   datos: schemas.CategoriaCrear) -> dict:
    curso = _curso_del_docente(db, docente, curso_id)
    _validar_categoria(db, curso.id, datos.nombre, datos.porcentajePeso)
    categoria = models.CategoriaEvaluacion(curso_id=curso.id, nombre=datos.nombre,
                                           porcentajePeso=datos.porcentajePeso)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return {"categoria": categoria, **_resumen_pesos(db, curso.id)}

def actualizar_categoria(db: Session, docente: models.Usuario, curso_id: int, categoria_id: int,
                         datos: schemas.CategoriaActualizar) -> dict:
    categoria = _categoria_del_curso(db, docente, curso_id, categoria_id)
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    _validar_categoria(db, categoria.curso_id, cambios.get("nombre", categoria.nombre),
                       cambios.get("porcentajePeso", categoria.porcentajePeso), categoria.id)
    for campo, valor in cambios.items():
        setattr(categoria, campo, valor)
    recalcular_acumuladas(db, categoria.curso_id)  # cambia lo que vale cada actividad
    db.commit()
    db.refresh(categoria)
    return {"categoria": categoria, **_resumen_pesos(db, categoria.curso_id)}

def eliminar_categoria(db: Session, docente: models.Usuario, curso_id: int, categoria_id: int) -> dict:
    categoria = _categoria_del_curso(db, docente, curso_id, categoria_id)
    if db.query(models.Actividad).filter_by(categoriaEvaluacion_id=categoria.id).first():
        raise HTTPException(409, "No se puede eliminar una categoría que ya tiene actividades")
    db.delete(categoria)
    db.commit()
    return listar_categorias(db, docente, curso_id)

# ======================================================================
# Actividades (RF-29, RF-30, RF-33 a RF-36) y archivos adjuntos (RNF-8)
# ======================================================================
def ahora() -> datetime:  # las pruebas lo reemplazan para fijar la fecha y hora
    return datetime.now()

def valores_actividades(db: Session, curso_id: int) -> dict[int, float]:
    """RF-34: las actividades de una categoría se reparten su peso por igual.
    Devuelve {actividad_id: porcentaje del curso que vale}."""
    filas = (db.query(models.Actividad.id, models.CategoriaEvaluacion.id,
                      models.CategoriaEvaluacion.porcentajePeso)
             .join(models.CategoriaEvaluacion,
                   models.CategoriaEvaluacion.id == models.Actividad.categoriaEvaluacion_id)
             .filter(models.CategoriaEvaluacion.curso_id == curso_id).all())
    por_categoria: dict[int, int] = {}
    for _, cat_id, _ in filas:
        por_categoria[cat_id] = por_categoria.get(cat_id, 0) + 1
    return {act_id: peso / por_categoria[cat_id] for act_id, cat_id, peso in filas}

def _actividad_dict(db: Session, a: models.Actividad, valores: dict[int, float] | None = None) -> dict:
    categoria = db.get(models.CategoriaEvaluacion, a.categoriaEvaluacion_id)
    if valores is None:
        valores = valores_actividades(db, categoria.curso_id)
    return {"id": a.id, "categoriaEvaluacion_id": categoria.id, "categoria": categoria.nombre,
            "titulo": a.titulo, "descripcion": a.descripcion, "fechaHoraLimite": a.fechaHoraLimite,
            "puntuacionMaxima": a.puntuacionMaxima, "valorEnCurso": round(valores[a.id], 2),
            "tieneArchivo": bool(a.archivoAdjunto)}

def _fecha_limite(valor: datetime) -> str:
    if valor.tzinfo:  # si llega con zona horaria, se pasa a la hora local del servidor
        valor = valor.astimezone().replace(tzinfo=None)
    if valor <= ahora():
        raise HTTPException(422, "La fecha límite debe ser posterior a la fecha y hora actuales")
    return valor.isoformat(timespec="seconds")

def _categoria_de(db: Session, curso_id: int, categoria_id: int) -> models.CategoriaEvaluacion:
    categoria = db.get(models.CategoriaEvaluacion, categoria_id)
    if not categoria or categoria.curso_id != curso_id:
        raise HTTPException(404, "Categoría no encontrada")
    return categoria

def _actividad_del_curso(db: Session, docente: models.Usuario, curso_id: int,
                         actividad_id: int) -> models.Actividad:
    curso = _curso_del_docente(db, docente, curso_id)
    actividad = db.get(models.Actividad, actividad_id)
    if not actividad or _curso_de_actividad(db, actividad) != curso.id:
        raise HTTPException(404, "Actividad no encontrada")
    return actividad

def _curso_de_actividad(db: Session, actividad: models.Actividad) -> int:
    return db.get(models.CategoriaEvaluacion, actividad.categoriaEvaluacion_id).curso_id

def listar_actividades(db: Session, docente: models.Usuario, curso_id: int) -> list[dict]:
    curso = _curso_del_docente(db, docente, curso_id)
    actividades = (db.query(models.Actividad)
                   .join(models.CategoriaEvaluacion,
                         models.CategoriaEvaluacion.id == models.Actividad.categoriaEvaluacion_id)
                   .filter(models.CategoriaEvaluacion.curso_id == curso.id)
                   .order_by(models.Actividad.fechaHoraLimite, models.Actividad.id).all())
    valores = valores_actividades(db, curso.id)
    return [_actividad_dict(db, a, valores) for a in actividades]

def ver_actividad(db: Session, docente: models.Usuario, curso_id: int, actividad_id: int) -> dict:
    return _actividad_dict(db, _actividad_del_curso(db, docente, curso_id, actividad_id))

def crearActividad(db: Session, docente: models.Usuario, curso_id: int,
                   datos: schemas.ActividadCrear) -> dict:
    curso = _curso_del_docente(db, docente, curso_id)
    if curso.estado != "activo":
        raise HTTPException(409, "El curso está archivado")
    categoria = _categoria_de(db, curso.id, datos.categoriaEvaluacion_id)
    actividad = models.Actividad(categoriaEvaluacion_id=categoria.id, titulo=datos.titulo,
                                 descripcion=datos.descripcion,
                                 fechaHoraLimite=_fecha_limite(datos.fechaHoraLimite),
                                 puntuacionMaxima=datos.puntuacionMaxima)
    db.add(actividad)
    recalcular_acumuladas(db, curso.id)  # RF-34: las demás de la categoría pasan a valer menos
    db.commit()
    db.refresh(actividad)
    return _actividad_dict(db, actividad)

def actualizar_actividad(db: Session, docente: models.Usuario, curso_id: int, actividad_id: int,
                         datos: schemas.ActividadActualizar) -> dict:
    actividad = _actividad_del_curso(db, docente, curso_id, actividad_id)
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    if "categoriaEvaluacion_id" in cambios:
        _categoria_de(db, curso_id, cambios["categoriaEvaluacion_id"])
    if "fechaHoraLimite" in cambios:
        cambios["fechaHoraLimite"] = _fecha_limite(cambios["fechaHoraLimite"])
    if "puntuacionMaxima" in cambios:
        mayor = (db.query(func.max(models.Calificacion.calificacionObtenida))
                 .join(models.Entrega, models.Entrega.id == models.Calificacion.entrega_id)
                 .filter(models.Entrega.actividad_id == actividad.id).scalar())
        if mayor is not None and cambios["puntuacionMaxima"] < mayor:
            raise HTTPException(409, "La puntuación máxima no puede ser menor que una calificación "
                                     f"ya asignada ({mayor:g})")
    for campo, valor in cambios.items():
        setattr(actividad, campo, valor)
    recalcular_acumuladas(db, curso_id)
    db.commit()
    db.refresh(actividad)
    return _actividad_dict(db, actividad)

def eliminar_actividad(db: Session, docente: models.Usuario, curso_id: int, actividad_id: int) -> list[dict]:
    actividad = _actividad_del_curso(db, docente, curso_id, actividad_id)
    if db.query(models.Entrega).filter_by(actividad_id=actividad.id).first():
        raise HTTPException(409, "No se puede eliminar una actividad que ya tiene entregas")
    archivo = actividad.archivoAdjunto
    db.delete(actividad)
    recalcular_acumuladas(db, curso_id)
    db.commit()
    _borrar_archivo(archivo)
    return listar_actividades(db, docente, curso_id)

def _guardar_archivo(subcarpeta: str, nombre_original: str, contenido: bytes) -> str:
    """RNF-8: valida tipo y tamaño y guarda en uploads/<subcarpeta>/. Devuelve la ruta relativa."""
    extension = Path(nombre_original or "").suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(415, "Tipo de archivo no permitido. Solo se aceptan PDF, Word (.doc, .docx), "
                                 "imágenes (.png, .jpg, .jpeg, .gif) y ZIP")
    if not contenido:
        raise HTTPException(422, "El archivo está vacío")
    if len(contenido) > TAMANO_MAXIMO_ARCHIVO:
        raise HTTPException(413, "El archivo supera el tamaño máximo de 10 MB")
    relativa = f"{subcarpeta}/{uuid.uuid4().hex}{extension}"  # nombre aleatorio: no se usa el del usuario
    destino = CARPETA_ARCHIVOS / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return relativa

def _borrar_archivo(relativa: str | None) -> None:
    if relativa:
        (CARPETA_ARCHIVOS / relativa).unlink(missing_ok=True)

def adjuntarArchivoActividad(db: Session, docente: models.Usuario, curso_id: int, actividad_id: int,
                             nombre_original: str, contenido: bytes) -> dict:
    """RF-36: reemplaza el archivo anterior, si había."""
    actividad = _actividad_del_curso(db, docente, curso_id, actividad_id)
    anterior = actividad.archivoAdjunto
    actividad.archivoAdjunto = _guardar_archivo("actividades", nombre_original, contenido)
    db.commit()
    _borrar_archivo(anterior)
    return _actividad_dict(db, actividad)

def quitar_archivo_actividad(db: Session, docente: models.Usuario, curso_id: int, actividad_id: int) -> dict:
    actividad = _actividad_del_curso(db, docente, curso_id, actividad_id)
    anterior = actividad.archivoAdjunto
    actividad.archivoAdjunto = None
    db.commit()
    _borrar_archivo(anterior)
    return _actividad_dict(db, actividad)

def archivo_de_actividad(db: Session, usuario: models.Usuario, actividad_id: int) -> tuple[Path, str]:
    """Lo descargan el docente del curso y sus alumnos activos. Devuelve (ruta, nombre de descarga)."""
    actividad = db.get(models.Actividad, actividad_id)
    if not actividad:
        raise HTTPException(404, "Actividad no encontrada")
    curso = db.get(models.Curso, _curso_de_actividad(db, actividad))
    inscrito = db.query(models.Matricula).filter_by(curso_id=curso.id, estudiante_id=usuario.id,
                                                    estado="activo").first()
    if curso.docente_id != usuario.id and not inscrito:
        raise HTTPException(403, "No tienes acceso a esta actividad")
    if not actividad.archivoAdjunto or not (CARPETA_ARCHIVOS / actividad.archivoAdjunto).is_file():
        raise HTTPException(404, "La actividad no tiene archivo adjunto")
    extension = Path(actividad.archivoAdjunto).suffix
    return CARPETA_ARCHIVOS / actividad.archivoAdjunto, f"{actividad.titulo}{extension}"

# ======================================================================
# Entregas del alumno (RF-37 a RF-39)
# ======================================================================
def _vencida(actividad: models.Actividad) -> bool:
    return ahora() > datetime.fromisoformat(actividad.fechaHoraLimite)

def _estado_entrega(actividad: models.Actividad, entrega: models.Entrega | None) -> str:
    if entrega:
        return "entregada_con_retraso" if entrega.entregadoConRetraso else "entregada"
    return "vencida" if _vencida(actividad) else "pendiente"

def _entrega_de(db: Session, actividad_id: int, matricula_id: int) -> models.Entrega | None:
    return db.query(models.Entrega).filter_by(actividad_id=actividad_id, matricula_id=matricula_id).first()

def _matricula_activa(db: Session, usuario: models.Usuario, curso_id: int) -> models.Matricula:
    curso = db.get(models.Curso, curso_id)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")
    matricula = db.query(models.Matricula).filter_by(curso_id=curso.id, estudiante_id=usuario.id,
                                                     estado="activo").first()
    if not matricula:
        raise HTTPException(403, "No estás inscrito en este curso")
    return matricula

def _actividad_del_alumno(db: Session, usuario: models.Usuario,
                          actividad_id: int) -> tuple[models.Actividad, models.Matricula]:
    actividad = db.get(models.Actividad, actividad_id)
    if not actividad:
        raise HTTPException(404, "Actividad no encontrada")
    return actividad, _matricula_activa(db, usuario, _curso_de_actividad(db, actividad))

def _actividad_alumno_dict(db: Session, a: models.Actividad, matricula: models.Matricula,
                           valores: dict[int, float] | None = None) -> dict:
    entrega = _entrega_de(db, a.id, matricula.id)
    return {**_actividad_dict(db, a, valores), "estadoEntrega": _estado_entrega(a, entrega),
            "entrega": entrega, "puedeCancelar": bool(entrega) and not _vencida(a)}

def cursos_del_alumno(db: Session, usuario: models.Usuario) -> list[models.Curso]:
    """Cursos con matrícula activa del alumno (incluye archivados para consultar su historial)."""
    return (db.query(models.Curso)
            .join(models.Matricula, models.Matricula.curso_id == models.Curso.id)
            .filter(models.Matricula.estudiante_id == usuario.id, models.Matricula.estado == "activo")
            .order_by(models.Curso.id).all())

def actividades_del_alumno(db: Session, usuario: models.Usuario, curso_id: int) -> list[dict]:
    matricula = _matricula_activa(db, usuario, curso_id)
    actividades = (db.query(models.Actividad)
                   .join(models.CategoriaEvaluacion,
                         models.CategoriaEvaluacion.id == models.Actividad.categoriaEvaluacion_id)
                   .filter(models.CategoriaEvaluacion.curso_id == matricula.curso_id)
                   .order_by(models.Actividad.fechaHoraLimite, models.Actividad.id).all())
    valores = valores_actividades(db, matricula.curso_id)
    return [_actividad_alumno_dict(db, a, matricula, valores) for a in actividades]

def entregarActividad(db: Session, usuario: models.Usuario, actividad_id: int,
                      nombre_original: str, contenido: bytes) -> dict:
    """RF-37: la fecha y hora las pone el servidor. RF-39: tarde se acepta, marcada con retraso."""
    actividad, matricula = _actividad_del_alumno(db, usuario, actividad_id)
    if db.get(models.Curso, matricula.curso_id).estado != "activo":
        raise HTTPException(409, "El curso está archivado")
    if _entrega_de(db, actividad.id, matricula.id):
        raise HTTPException(409, "Ya entregaste esta actividad; cancela tu entrega para volver a subirla")
    momento = ahora()
    archivo = _guardar_archivo("entregas", nombre_original, contenido)
    db.add(models.Entrega(actividad_id=actividad.id, matricula_id=matricula.id, archivoDigital=archivo,
                          fechaHoraEntrega=momento.isoformat(timespec="seconds"),
                          entregadoConRetraso=int(_vencida(actividad))))
    db.commit()
    return _actividad_alumno_dict(db, actividad, matricula)

def cancelarEntrega(db: Session, usuario: models.Usuario, actividad_id: int) -> dict:
    """RF-38: solo antes de la fecha límite; después la entrega queda fija."""
    actividad, matricula = _actividad_del_alumno(db, usuario, actividad_id)
    entrega = _entrega_de(db, actividad.id, matricula.id)
    if not entrega:
        raise HTTPException(404, "No has entregado esta actividad")
    if _vencida(actividad):
        raise HTTPException(409, "Ya pasó la fecha límite; no puedes cancelar tu entrega")
    if db.query(models.Calificacion).filter_by(entrega_id=entrega.id).first():
        raise HTTPException(409, "Tu entrega ya fue calificada; no puedes cancelarla")
    archivo = entrega.archivoDigital
    db.delete(entrega)
    db.commit()
    _borrar_archivo(archivo)
    return _actividad_alumno_dict(db, actividad, matricula)

def entregas_de_actividad(db: Session, docente: models.Usuario, curso_id: int, actividad_id: int) -> list[dict]:
    """Para el docente: cada alumno activo con su entrega (o sin ella)."""
    actividad = _actividad_del_curso(db, docente, curso_id, actividad_id)
    entregas = {e.matricula_id: e for e in db.query(models.Entrega).filter_by(actividad_id=actividad.id).all()}
    return [{**_datos_alumno(m, e, u), "entrega": entregas.get(m.id),
             "estadoEntrega": _estado_entrega(actividad, entregas.get(m.id))}
            for m, e, u in _alumnos_activos(db, curso_id)]

def archivo_de_entrega(db: Session, usuario: models.Usuario, entrega_id: int) -> tuple[Path, str]:
    """Lo descargan el alumno que entregó y el docente del curso. Devuelve (ruta, nombre de descarga)."""
    entrega = db.get(models.Entrega, entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega no encontrada")
    matricula = db.get(models.Matricula, entrega.matricula_id)
    curso = db.get(models.Curso, matricula.curso_id)
    if usuario.id not in (matricula.estudiante_id, curso.docente_id):
        raise HTTPException(403, "No tienes acceso a esta entrega")
    if not entrega.archivoDigital or not (CARPETA_ARCHIVOS / entrega.archivoDigital).is_file():
        raise HTTPException(404, "La entrega no tiene archivo")
    actividad = db.get(models.Actividad, entrega.actividad_id)
    codigo = db.get(models.Estudiante, matricula.estudiante_id).codigoEstudiante
    extension = Path(entrega.archivoDigital).suffix
    return CARPETA_ARCHIVOS / entrega.archivoDigital, f"{codigo}_{actividad.titulo}{extension}"

# ======================================================================
# Calificaciones (RF-43, RF-46, RF-47, RF-67)
# ======================================================================
def calcular_calificacion(items: list[tuple[float, float, float | None, bool]]) -> dict:
    """Cada item es (valorEnCurso, puntuacionMaxima, calificacionObtenida o None, vencida sin entrega).
    - RF-46: la acumulada son los puntos ganados sobre 100 según los pesos.
    - RF-47: vencida sin entrega cuenta como 0, pero sí suma a los puntos posibles.
    - Lo pendiente (aún no vence, o entregado sin calificar) no cuenta en ninguno de los dos.
    El desempeño proporcional (acumulada / posibles) es el que usará la alerta de RF-48."""
    ganados = posibles = 0.0
    for valor, maximo, obtenida, cero in items:
        if obtenida is not None:
            ganados += valor * obtenida / maximo
            posibles += valor
        elif cero:
            posibles += valor
    return {"calificacionAcumulada": round(ganados, 2), "puntosPosibles": round(posibles, 2),
            "desempenoProporcional": round(ganados * 100 / posibles, 2) if posibles else None}

def _actividades_de_curso(db: Session, curso_id: int) -> list[models.Actividad]:
    return (db.query(models.Actividad)
            .join(models.CategoriaEvaluacion,
                  models.CategoriaEvaluacion.id == models.Actividad.categoriaEvaluacion_id)
            .filter(models.CategoriaEvaluacion.curso_id == curso_id)
            .order_by(models.Actividad.fechaHoraLimite, models.Actividad.id).all())

def _datos_calificaciones(db: Session, curso_id: int) -> tuple[list, dict, dict, dict]:
    """Actividades, valores, entregas {(matricula, actividad): Entrega} y calificaciones {entrega: Calificacion}."""
    actividades = _actividades_de_curso(db, curso_id)
    entregas = {(e.matricula_id, e.actividad_id): e for e in db.query(models.Entrega)
                .filter(models.Entrega.actividad_id.in_([a.id for a in actividades])).all()}
    calificaciones = {c.entrega_id: c for c in db.query(models.Calificacion)
                      .filter(models.Calificacion.entrega_id.in_([e.id for e in entregas.values()])).all()}
    return actividades, valores_actividades(db, curso_id), entregas, calificaciones

def _fila_calificaciones(matricula_id: int, actividades, valores, entregas, calificaciones) -> dict:
    celdas, items = [], []
    for a in actividades:
        entrega = entregas.get((matricula_id, a.id))
        calif = calificaciones.get(entrega.id) if entrega else None
        cero = entrega is None and _vencida(a)
        celdas.append({"actividad_id": a.id, "estadoEntrega": _estado_entrega(a, entrega),
                       "entrega_id": entrega.id if entrega else None, "calificacion": calif,
                       "cuentaComoCero": cero})
        items.append((valores[a.id], a.puntuacionMaxima, calif.calificacionObtenida if calif else None, cero))
    return {"celdas": celdas, **calcular_calificacion(items)}

def _columnas(db: Session, actividades, valores) -> list[dict]:
    return [{"id": a.id, "titulo": a.titulo, "fechaHoraLimite": a.fechaHoraLimite,
             "categoria": db.get(models.CategoriaEvaluacion, a.categoriaEvaluacion_id).nombre,
             "puntuacionMaxima": a.puntuacionMaxima, "valorEnCurso": round(valores[a.id], 2)}
            for a in actividades]

def recalcular_acumuladas(db: Session, curso_id: int) -> None:
    """RF-67: guarda en Matricula.calificacionAcumuladaActual la acumulada de cada alumno activo.
    Se llama al calificar y cuando cambian pesos o actividades. No hace commit."""
    db.flush()
    datos = _datos_calificaciones(db, curso_id)
    for m in db.query(models.Matricula).filter_by(curso_id=curso_id, estado="activo").all():
        m.calificacionAcumuladaActual = _fila_calificaciones(m.id, *datos)["calificacionAcumulada"]

def calificarEntrega(db: Session, docente: models.Usuario, curso_id: int, entrega_id: int,
                     datos: schemas.CalificacionCrear) -> dict:
    """RF-43: de 0 a la puntuación máxima. Si ya estaba calificada, se corrige."""
    curso = _curso_del_docente(db, docente, curso_id)
    entrega = db.get(models.Entrega, entrega_id)
    matricula = db.get(models.Matricula, entrega.matricula_id) if entrega else None
    if not matricula or matricula.curso_id != curso.id:
        raise HTTPException(404, "Entrega no encontrada")
    if matricula.estado != "activo":
        raise HTTPException(409, "El alumno ya no está activo en el curso")
    actividad = db.get(models.Actividad, entrega.actividad_id)
    if datos.calificacionObtenida > actividad.puntuacionMaxima:
        raise HTTPException(422, f"La calificación debe estar entre 0 y {actividad.puntuacionMaxima:g}")

    calificacion = db.query(models.Calificacion).filter_by(entrega_id=entrega.id).first()
    if not calificacion:
        calificacion = models.Calificacion(entrega_id=entrega.id)
        db.add(calificacion)
    calificacion.calificacionObtenida = datos.calificacionObtenida
    calificacion.retroalimentacion = datos.retroalimentacion
    calificacion.fecha = ahora().isoformat(timespec="seconds")
    recalcular_acumuladas(db, curso.id)
    db.commit()
    return {"entrega_id": entrega.id, "matricula_id": matricula.id, "calificacion": calificacion,
            "calificacionAcumuladaActual": matricula.calificacionAcumuladaActual}

def cuadricula_calificaciones(db: Session, docente: models.Usuario, curso_id: int) -> dict:
    """Columnas = actividades por fecha límite; filas = alumnos activos con su acumulada."""
    curso = _curso_del_docente(db, docente, curso_id)
    datos = _datos_calificaciones(db, curso.id)
    return {"curso_id": curso.id, "actividades": _columnas(db, datos[0], datos[1]),
            "alumnos": [{**_datos_alumno(m, e, u), **_fila_calificaciones(m.id, *datos)}
                        for m, e, u in _alumnos_activos(db, curso.id)]}

def calificaciones_del_alumno(db: Session, usuario: models.Usuario, curso_id: int) -> dict:
    matricula = _matricula_activa(db, usuario, curso_id)
    datos = _datos_calificaciones(db, matricula.curso_id)
    return {"curso_id": matricula.curso_id, "actividades": _columnas(db, datos[0], datos[1]),
            **_fila_calificaciones(matricula.id, *datos)}

# ======================================================================
# Baja de alumno (RF-16) y seguimiento: alerta y semáforo (RF-48, RF-49, RF-61)
# ======================================================================
def cambiar_estado_matricula(db: Session, docente: models.Usuario, curso_id: int, matricula_id: int,
                             estado: str) -> dict:
    """RF-16: un alumno de baja deja de aparecer en asistencia y calificaciones; se puede reactivar."""
    curso = _curso_del_docente(db, docente, curso_id)
    matricula = db.get(models.Matricula, matricula_id)
    if not matricula or matricula.curso_id != curso.id:
        raise HTTPException(404, "El alumno no está inscrito en este curso")
    matricula.estado = estado
    recalcular_acumuladas(db, curso.id)  # al reactivarlo su acumulada vuelve a estar al día
    db.commit()
    return next(a for a in alumnos_de_curso(db, docente, curso.id) if a["matricula_id"] == matricula.id)

def alerta_calificacion(desempeno: float | None) -> bool:
    """RF-48: se compara el desempeño proporcional, no la acumulada absoluta."""
    return desempeno is not None and desempeno < DESEMPENO_ALERTA

def semaforo_calificacion(desempeno: float | None) -> str:
    """Verde >= 70 %, amarillo de 60 % a < 70 %, rojo < 60 %. Sin nada evaluado: verde."""
    if desempeno is None or desempeno >= SEMAFORO_CALIFICACION_VERDE:
        return "verde"
    return "rojo" if alerta_calificacion(desempeno) else "amarillo"

def semaforo_general(*semaforos: str) -> str:
    """RF-61: el peor de los semáforos de la materia."""
    return max(semaforos, key=ORDEN_SEMAFORO.index)

def _indicadores(asistencia: float, calificacion: dict) -> dict:
    desempeno = calificacion["desempenoProporcional"]
    sem_asistencia, sem_calificacion = semaforo_asistencia(asistencia), semaforo_calificacion(desempeno)
    return {"porcentajeAsistencia": round(asistencia, 2), "estatusNormativo": estatus_normativo(asistencia),
            "semaforoAsistencia": sem_asistencia,
            "calificacionAcumulada": calificacion["calificacionAcumulada"],
            "puntosPosibles": calificacion["puntosPosibles"], "desempenoProporcional": desempeno,
            "alertaCalificacion": alerta_calificacion(desempeno),
            "semaforoCalificacion": sem_calificacion,
            "semaforoGeneral": semaforo_general(sem_asistencia, sem_calificacion)}

def seguimiento_de_curso(db: Session, docente: models.Usuario, curso_id: int) -> dict:
    curso = _curso_del_docente(db, docente, curso_id)
    datos = _datos_calificaciones(db, curso.id)
    alumnos = [{**_datos_alumno(m, e, u),
                **_indicadores(porcentaje_asistencia(db, m.id), _fila_calificaciones(m.id, *datos))}
               for m, e, u in _alumnos_activos(db, curso.id)]
    resumen = {color: sum(a["semaforoGeneral"] == color for a in alumnos) for color in ORDEN_SEMAFORO}
    return {"curso_id": curso.id, "resumen": resumen, "alumnos": alumnos}

def seguimiento_del_alumno(db: Session, usuario: models.Usuario, curso_id: int) -> dict:
    matricula = _matricula_activa(db, usuario, curso_id)
    datos = _datos_calificaciones(db, matricula.curso_id)
    return {"curso_id": matricula.curso_id,
            **_indicadores(porcentaje_asistencia(db, matricula.id), _fila_calificaciones(matricula.id, *datos))}
