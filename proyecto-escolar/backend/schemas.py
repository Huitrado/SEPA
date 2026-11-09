import re
from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import (AfterValidator, BaseModel, BeforeValidator, ConfigDict, EmailStr,
                      Field, StringConstraints, field_validator, model_validator)

from config import DOMINIOS_ROL, dominio_de, fechas_ciclo, rol_por_correo

# ------------------------------------------------------------------ tipos reutilizables
def _a_texto(v):
    return str(v) if isinstance(v, int) and not isinstance(v, bool) else v

def _nombre(v: str) -> str:
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]*", v):
        raise ValueError("Solo puede contener letras, espacios, apóstrofes y guiones")
    return v

def _codigo_estudiante(v: str) -> str:
    if not re.fullmatch(r"\d{9}", v):
        raise ValueError("El código de estudiante debe tener 9 dígitos")
    return v

def _contrasena(v: str) -> str:  # RF-03
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if len(v) > 72:  # límite de bcrypt
        raise ValueError("La contraseña no puede tener más de 72 caracteres")
    if not re.search(r"[a-z]", v):
        raise ValueError("La contraseña debe incluir al menos una letra minúscula")
    if not re.search(r"[A-Z]", v):
        raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
    if not re.search(r"\d", v):
        raise ValueError("La contraseña debe incluir al menos un número")
    return v

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Nombre = Annotated[Texto, AfterValidator(_nombre)]
CodigoEstudiante = Annotated[str, BeforeValidator(_a_texto),
                             StringConstraints(strip_whitespace=True, min_length=1),
                             AfterValidator(_codigo_estudiante)]
CodigoEmpleado = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=3,
                                                  max_length=20, pattern=r"^[A-Za-z0-9-]+$")]
Contrasena = Annotated[str, AfterValidator(_contrasena)]
CorreoNormalizado = Annotated[EmailStr, AfterValidator(lambda c: c.lower())]  # 'Ana@..' == 'ana@..'
Clave = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=2,
                                         max_length=10, pattern=r"^[A-Za-z0-9]+$")]
Seccion = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=10)]
Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

Dia = Literal["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
TipoEvaluacion = Literal["numerica", "aprobado_no_aprobado"]

# ------------------------------------------------------------------ módulo: registro y login
class UsuarioCrear(BaseModel):  # RF-01, RF-02, RF-03
    nombre: Nombre
    apellidos: Nombre
    correoInstitucional: CorreoNormalizado
    contrasena: Contrasena
    confirmarContrasena: str
    # Solo estudiantes (@alumnos.udg.mx)
    codigo: CodigoEstudiante | None = None
    carrera: Clave | None = None
    ciclo: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1)] | None = None
    # Solo docentes (@academicos.udg.mx)
    noEmpleado: CodigoEmpleado | None = None
    departamento: str | None = None

    @model_validator(mode="after")
    def validar_formulario(self):
        if self.contrasena != self.confirmarContrasena:
            raise ValueError("La contraseña y su confirmación no coinciden")
        rol = rol_por_correo(self.correoInstitucional)
        if rol is None:
            dominios = " o ".join(f"@{d}" for d in DOMINIOS_ROL)
            raise ValueError(f"Solo se aceptan correos institucionales ({dominios})")
        if rol == "estudiante" and None in (self.codigo, self.carrera, self.ciclo):
            raise ValueError("Los estudiantes deben enviar código, carrera y ciclo")
        if rol == "docente" and not self.noEmpleado:
            raise ValueError("Los docentes deben enviar su número de empleado")
        return self

class UsuarioLogin(BaseModel):  # RF-04: se entra con el código, no con el correo
    codigo: Annotated[str, BeforeValidator(_a_texto),
                      StringConstraints(strip_whitespace=True, to_upper=True, min_length=1)]
    contrasena: str = Field(min_length=1)

class UsuarioSalida(BaseModel):  # nunca incluye la contraseña
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    apellidos: str
    correoInstitucional: EmailStr

class RegistroSalida(UsuarioSalida):
    estado: str
    rol: str
    mensaje: str

class SesionSalida(BaseModel):
    access_token: str
    token_type: str
    roles: list[str]
    panel: str | None  # RF-90: a qué panel de inicio redirigir
    nombre: str

class PerfilSalida(UsuarioSalida):
    codigo: str | None
    roles: list[str]
    panel: str | None

# ------------------------------------------------------------------ administración
class PersonalCrear(BaseModel):
    nombre: Nombre
    apellidos: Nombre
    correoInstitucional: CorreoNormalizado
    contrasena: Contrasena
    noEmpleado: CodigoEmpleado

class DocenteCrear(PersonalCrear):
    departamento: str | None = None

    @field_validator("correoInstitucional")
    @classmethod
    def correo_de_docente(cls, v):
        if rol_por_correo(v) != "docente":
            raise ValueError(f"El correo de un docente debe terminar en @{dominio_de('docente')}")
        return v

class AdminCrear(PersonalCrear):
    pass

class UsuarioAdminSalida(UsuarioSalida):
    estado: str
    roles: list[str]

class EstadoUsuario(BaseModel):
    estado: Literal["activo", "inactivo"]

class NuevaContrasena(BaseModel):
    nueva_contrasena: Contrasena

class CarreraCrear(BaseModel):  # RF-02: catálogo oficial de carreras
    clave: Clave
    nombre: Texto

class CarreraSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    clave: str
    nombre: str

class MateriaSalida(BaseModel):  # RF-12: catálogo de materias (de planes.json)
    model_config = ConfigDict(from_attributes=True)
    id: int
    clave: str
    nombre: str

class CicloCrear(BaseModel):  # RF-08: el nombre es AAAA-A o AAAA-B y las fechas salen del calendario oficial
    nombreOficial: str
    fechaInicio: date | None = None    # opcional: si se omite, se usa la fecha oficial
    fechaTermino: date | None = None

    @model_validator(mode="after")
    def validar_calendario(self):
        self.nombreOficial = self.nombreOficial.strip().upper()
        oficiales = fechas_ciclo(self.nombreOficial)
        if oficiales is None:
            raise ValueError("El nombre del ciclo debe tener el formato AAAA-A o AAAA-B (por ejemplo 2026-B)")
        inicio, termino = oficiales
        if self.fechaInicio not in (None, inicio) or self.fechaTermino not in (None, termino):
            raise ValueError(f"El ciclo {self.nombreOficial} va del {inicio:%d/%m/%Y} al {termino:%d/%m/%Y}")
        self.fechaInicio, self.fechaTermino = inicio, termino
        return self

class CicloSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombreOficial: str
    fechaInicio: str
    fechaTermino: str
    estado: str

class ReasignarDocente(BaseModel):
    docente_id: int

# ------------------------------------------------------------------ módulo: gestión académica
def _sin_repetidos(v: list) -> list:
    if len(set(v)) != len(v):
        raise ValueError("Los días de la semana no pueden repetirse")
    return v

DiasSemana = Annotated[list[Dia], Field(min_length=1), AfterValidator(_sin_repetidos)]

class CursoCrear(BaseModel):  # RF-09, RF-12, RF-13, RF-17 (RF-18 lo fija el servidor)
    nombreMateria: Texto
    seccion: Seccion
    descripcion: Descripcion
    cicloEscolar_id: int  # RF-09: obligatorio
    tipoEvaluacion: TipoEvaluacion
    diasSemana: DiasSemana
    horaInicio: time
    horaFin: time

    @model_validator(mode="after")
    def horario_valido(self):
        if self.horaFin <= self.horaInicio:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self

class CursoActualizar(BaseModel):  # todo opcional: solo se cambia lo que se envía
    nombreMateria: Texto | None = None
    seccion: Seccion | None = None
    descripcion: Descripcion | None = None
    tipoEvaluacion: TipoEvaluacion | None = None
    diasSemana: DiasSemana | None = None
    horaInicio: time | None = None
    horaFin: time | None = None

def _dias_a_lista(v):
    return v.split(",") if isinstance(v, str) else v

class CursoPublico(BaseModel):  # listado general: sin el código de acceso
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombreMateria: str
    seccion: str
    descripcion: str | None
    estado: str
    tipoEvaluacion: str
    umbralNumerico: float
    cicloEscolar_id: int | None
    diasSemana: Annotated[list[str], BeforeValidator(_dias_a_lista)]
    horaInicio: str
    horaFin: str
    docente_id: int | None

class CursoSalida(CursoPublico):  # solo lo ve el docente del curso y el administrador
    codigoCurso: str

class EstadoCurso(BaseModel):  # RF-10
    estado: Literal["activo", "archivado"]

class InscripcionCrear(BaseModel):  # RF-15
    codigoCurso: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True,
                                                  min_length=1, max_length=10)]

class AlumnoCurso(BaseModel):  # RF-16
    matricula_id: int
    estudiante_id: int
    codigoEstudiante: str
    nombre: str
    apellidos: str
    correoInstitucional: EmailStr
    estado: str
    fechaInscripcion: str
    calificacionAcumuladaActual: float | None

# ------------------------------------------------------------------ módulo: control de asistencia
EstadoAsistencia = Literal["asistencia", "falta", "retardo"]

class SesionClaseCrear(BaseModel):  # RF-19: fecha y horario los pone el servidor
    tema: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None

class AsistenciaAlumno(BaseModel):  # RF-20, RF-23
    matricula_id: int
    estado: EstadoAsistencia
    observaciones: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None

class ListaAsistencia(BaseModel):
    asistencias: list[AsistenciaAlumno]

    @field_validator("asistencias")
    @classmethod
    def sin_alumnos_repetidos(cls, v):
        if len({a.matricula_id for a in v}) != len(v):
            raise ValueError("Un alumno aparece más de una vez en la lista")
        return v

class SesionClaseSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    curso_id: int
    fecha: str
    horaInicio: str
    horaFin: str
    tema: str | None
    listaGuardada: bool  # False = pendiente: no cuenta en el porcentaje (RF-22)

class AsistenciaEnLista(BaseModel):
    matricula_id: int
    estudiante_id: int
    codigoEstudiante: str
    nombre: str
    apellidos: str
    estado: str  # asistencia | falta | retardo | pendiente
    observaciones: str | None

class SesionClaseDetalle(SesionClaseSalida):  # una sesión con la lista de sus alumnos
    alumnos: list[AsistenciaEnLista]

class EstadoEnSesion(BaseModel):
    sesion_id: int
    estado: str | None  # None: el alumno aún no estaba inscrito cuando se generó la sesión
    observaciones: str | None

class FilaAsistencia(BaseModel):  # RF-24, RF-26: un alumno en la cuadrícula
    matricula_id: int
    estudiante_id: int
    codigoEstudiante: str
    nombre: str
    apellidos: str
    estados: list[EstadoEnSesion]  # en el mismo orden que CuadriculaAsistencia.sesiones
    porcentajeAsistencia: float
    estatusNormativo: Literal["Ordinario", "Extraordinario", "Sin Derecho"]  # RF-49
    semaforo: Literal["verde", "amarillo", "rojo"]

class CuadriculaAsistencia(BaseModel):
    curso_id: int
    sesiones: list[SesionClaseSalida]  # ordenadas por fecha
    alumnos: list[FilaAsistencia]

# ------------------------------------------------------------------ módulo: categorías de evaluación
PesoCategoria = Annotated[float, Field(gt=0, le=100)]  # RF-31: porcentaje del total del curso

class CategoriaCrear(BaseModel):  # RF-31
    nombre: Texto
    porcentajePeso: PesoCategoria

class CategoriaActualizar(BaseModel):  # solo se cambia lo que se envía
    nombre: Texto | None = None
    porcentajePeso: PesoCategoria | None = None

class CategoriaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    curso_id: int
    nombre: str
    porcentajePeso: float

class ResumenPesos(BaseModel):  # RF-32
    sumaPesos: float
    pesosCompletos: bool       # True solo si la suma es exactamente 100
    advertencia: str | None    # en español cuando la suma no es 100

class CategoriasCurso(ResumenPesos):
    categorias: list[CategoriaSalida]

class CategoriaGuardada(ResumenPesos):
    categoria: CategoriaSalida

# ------------------------------------------------------------------ módulo: actividades
Puntuacion = Annotated[float, Field(gt=0, le=1000)]
DescripcionLarga = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]

class ActividadCrear(BaseModel):
    categoriaEvaluacion_id: int
    titulo: Texto
    descripcion: DescripcionLarga | None = None
    fechaHoraLimite: datetime
    puntuacionMaxima: Puntuacion

class ActividadActualizar(BaseModel):  # solo se cambia lo que se envía
    categoriaEvaluacion_id: int | None = None
    titulo: Texto | None = None
    descripcion: DescripcionLarga | None = None
    fechaHoraLimite: datetime | None = None
    puntuacionMaxima: Puntuacion | None = None

class ActividadSalida(BaseModel):
    id: int
    categoriaEvaluacion_id: int
    categoria: str
    titulo: str
    descripcion: str | None
    fechaHoraLimite: str
    puntuacionMaxima: float
    valorEnCurso: float  # RF-34: peso de la categoría / número de actividades de esa categoría
    tieneArchivo: bool   # RF-36

# ------------------------------------------------------------------ módulo: entregas
EstadoEntrega = Literal["pendiente", "vencida", "entregada", "entregada_con_retraso"]

class EntregaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actividad_id: int
    matricula_id: int
    fechaHoraEntrega: str       # RF-37: la pone el servidor
    entregadoConRetraso: bool   # RF-39

class ActividadAlumno(BaseModel):  # una actividad vista por el alumno, con su entrega
    id: int
    categoria: str
    titulo: str
    descripcion: str | None
    fechaHoraLimite: str
    puntuacionMaxima: float
    valorEnCurso: float
    tieneArchivo: bool
    estadoEntrega: EstadoEntrega  # "vencida": sin entrega y ya pasó la fecha (aún se acepta tarde)
    entrega: EntregaSalida | None
    puedeCancelar: bool           # RF-38: hay entrega y aún no llega la fecha límite

class EntregaDeAlumno(BaseModel):  # lo que ve el docente por cada alumno activo
    matricula_id: int
    estudiante_id: int
    codigoEstudiante: str
    nombre: str
    apellidos: str
    estadoEntrega: EstadoEntrega
    entrega: EntregaSalida | None
