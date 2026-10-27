from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

# Tabla de asociación muchos a muchos
usuario_rol = Table(
    "UsuarioRol",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("Usuario.id"), primary_key=True),
    Column("rol_id", Integer, ForeignKey("Rol.id"), primary_key=True)
)

class Usuario(Base):
    __tablename__ = "Usuario"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    correoInstitucional = Column(String, unique=True, nullable=False)
    contrasena = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    fechaRegistro = Column(String, nullable=False)

class Rol(Base):
    __tablename__ = "Rol"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, unique=True, nullable=False)

class Administrador(Base):
    __tablename__ = "Administrador"
    id = Column(Integer, ForeignKey("Usuario.id"), primary_key=True)
    noEmpleado = Column(String, unique=True, nullable=False)

class Docente(Base):
    __tablename__ = "Docente"
    id = Column(Integer, ForeignKey("Usuario.id"), primary_key=True)
    noEmpleado = Column(String, unique=True, nullable=False)
    departamento = Column(String)

class MallaCurricular(Base):
    __tablename__ = "MallaCurricular"
    id = Column(Integer, primary_key=True, autoincrement=True)
    carrera = Column(String, nullable=False)
    generacion = Column(String, nullable=False)
    nombrePlan = Column(String, nullable=False)

class Estudiante(Base):
    __tablename__ = "Estudiante"
    id = Column(Integer, ForeignKey("Usuario.id"), primary_key=True)
    codigoEstudiante = Column(String, unique=True, nullable=False)
    carrera = Column(String)
    ciclo = Column(String)
    mallaCurricular_id = Column(Integer, ForeignKey("MallaCurricular.id"))

class CicloEscolar(Base):
    __tablename__ = "CicloEscolar"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombreOficial = Column(String, nullable=False)
    fechaInicio = Column(String, nullable=False)
    fechaTermino = Column(String, nullable=False)
    estado = Column(String, nullable=False)

class Curso(Base):
    __tablename__ = "Curso"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombreMateria = Column(String, nullable=False)
    seccion = Column(String, nullable=False)
    descripcion = Column(String)
    codigoCurso = Column(String, unique=True, nullable=False)
    estado = Column(String, nullable=False)
    tipoEvaluacion = Column(String, nullable=False)
    umbralNumerico = Column(Float, nullable=False)
    diasSemana = Column(String, nullable=False)
    horaInicio = Column(String, nullable=False)
    horaFin = Column(String, nullable=False)
    cicloEscolar_id = Column(Integer, ForeignKey("CicloEscolar.id"))
    docente_id = Column(Integer, ForeignKey("Docente.id"))
    materia_id = Column(Integer, ForeignKey("Materia.id"))

class Matricula(Base):
    __tablename__ = "Matricula"
    __table_args__ = (UniqueConstraint("curso_id", "estudiante_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    fechaInscripcion = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    calificacionAcumuladaActual = Column(Float)
    curso_id = Column(Integer, ForeignKey("Curso.id"))
    estudiante_id = Column(Integer, ForeignKey("Estudiante.id"))

class HistorialAcademico(Base):
    __tablename__ = "HistorialAcademico"
    id = Column(Integer, primary_key=True, autoincrement=True)
    periodo = Column(String, nullable=False)
    materia = Column(String, nullable=False)
    calificacion = Column(Float, nullable=False)
    resultado = Column(String, nullable=False)
    estudiante_id = Column(Integer, ForeignKey("Estudiante.id"))
    materia_id = Column(Integer, ForeignKey("Materia.id"))

class PublicacionAsesoria(Base):
    __tablename__ = "PublicacionAsesoria"
    id = Column(Integer, primary_key=True, autoincrement=True)
    materia = Column(String, nullable=False)
    horario = Column(String, nullable=False)
    modalidad = Column(String, nullable=False)
    lugarOMedio = Column(String, nullable=False)
    topico = Column(String)
    estado = Column(String, nullable=False)
    estudiante_id = Column(Integer, ForeignKey("Estudiante.id"))

class BibliotecaNormatividad(Base):
    __tablename__ = "BibliotecaNormatividad"
    id = Column(Integer, primary_key=True, autoincrement=True)
    extractosReglamento = Column(String)
    guiaSIATCE = Column(String)
    directorioCoordinacion = Column(String)
    checklistSupervivencia = Column(String)

class SesionClase(Base):
    __tablename__ = "SesionClase"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(String, nullable=False)
    horaInicio = Column(String, nullable=False)
    horaFin = Column(String, nullable=False)
    tema = Column(String)
    listaGuardada = Column(Integer, nullable=False)
    curso_id = Column(Integer, ForeignKey("Curso.id"))

class Asistencia(Base):
    __tablename__ = "Asistencia"
    id = Column(Integer, primary_key=True, autoincrement=True)
    estado = Column(String, nullable=False)
    observaciones = Column(String)
    sesionClase_id = Column(Integer, ForeignKey("SesionClase.id"))
    matricula_id = Column(Integer, ForeignKey("Matricula.id"))

class RegistroRiesgo(Base):
    __tablename__ = "RegistroRiesgo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    semaforo = Column(String, nullable=False)
    estadoInformativo = Column(String, nullable=False)
    riesgoPorHistorial = Column(Integer, nullable=False)
    riesgoCritico = Column(Integer, nullable=False)
    detalleCausaRezago = Column(String)
    matricula_id = Column(Integer, ForeignKey("Matricula.id"))

class CategoriaEvaluacion(Base):
    __tablename__ = "CategoriaEvaluacion"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    porcentajePeso = Column(Float, nullable=False)
    curso_id = Column(Integer, ForeignKey("Curso.id"))

class Actividad(Base):
    __tablename__ = "Actividad"
    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(String)
    fechaHoraLimite = Column(String, nullable=False)
    puntuacionMaxima = Column(Float, nullable=False)
    categoriaEvaluacion_id = Column(Integer, ForeignKey("CategoriaEvaluacion.id"))

class Entrega(Base):
    __tablename__ = "Entrega"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fechaHoraEntrega = Column(String, nullable=False)
    archivoDigital = Column(String)
    entregadoConRetraso = Column(Integer, nullable=False)
    actividad_id = Column(Integer, ForeignKey("Actividad.id"))
    matricula_id = Column(Integer, ForeignKey("Matricula.id"))

class Calificacion(Base):
    __tablename__ = "Calificacion"
    id = Column(Integer, primary_key=True, autoincrement=True)
    calificacionObtenida = Column(Float, nullable=False)
    retroalimentacion = Column(String)
    fecha = Column(String, nullable=False)
    entrega_id = Column(Integer, ForeignKey("Entrega.id"))


class Carrera(Base):
    __tablename__ = "Carrera"
    id = Column(Integer, primary_key=True, autoincrement=True)
    clave = Column(String, unique=True, nullable=False)
    nombre = Column(String, unique=True, nullable=False)


class TokenRevocado(Base):
    __tablename__ = "TokenRevocado"
    jti = Column(String, primary_key=True)
    expira = Column(String, nullable=False)

class Materia(Base):
    __tablename__ = "Materia"
    id = Column(Integer, primary_key=True, autoincrement=True)
    clave = Column(String, unique=True, nullable=False)
    nombre = Column(String, nullable=False)

class MallaMateria(Base):
    __tablename__ = "MallaMateria"
    __table_args__ = (UniqueConstraint("mallaCurricular_id", "materia_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    semestreBase = Column(Integer, nullable=False)
    mallaCurricular_id = Column(Integer, ForeignKey("MallaCurricular.id"), nullable=False)
    materia_id = Column(Integer, ForeignKey("Materia.id"), nullable=False)