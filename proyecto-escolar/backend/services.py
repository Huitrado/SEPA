"""Lógica de negocio. Los routers solo reciben, delegan aquí y responden."""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from config import (CARRERAS_INICIALES, DIAS_SEMANA, DOCENTE_REQUIERE_APROBACION,
                    PRIORIDAD_PANEL, UMBRAL_APROBATORIO, rol_por_correo)
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
