import sqlite3

# Conectar a la base de datos (se creará o actualizará el archivo)
conexion = sqlite3.connect("sistema_escolar.db")
cursor = conexion.cursor()

# Activar validación de llaves foráneas
cursor.execute("PRAGMA foreign_keys = ON;")


# Tabla Usuario
cursor.execute('''CREATE TABLE IF NOT EXISTS Usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    correoInstitucional TEXT UNIQUE NOT NULL,
    contrasena TEXT NOT NULL,
    rol TEXT NOT NULL,
    estado TEXT NOT NULL,
    fechaRegistro TEXT NOT NULL
)''')


# Tabla Administrador
cursor.execute('''CREATE TABLE IF NOT EXISTS Administrador (
    id INTEGER PRIMARY KEY,
    noEmpleado TEXT UNIQUE NOT NULL,
    FOREIGN KEY (id) REFERENCES Usuario(id)
)''')


# Tabla Docente
cursor.execute('''CREATE TABLE IF NOT EXISTS Docente (
    id INTEGER PRIMARY KEY,
    noEmpleado TEXT UNIQUE NOT NULL,
    departamento TEXT,
    FOREIGN KEY (id) REFERENCES Usuario(id)
)''')


# Tabla Estudiante
cursor.execute('''CREATE TABLE IF NOT EXISTS Estudiante (
    id INTEGER PRIMARY KEY,
    codigoEstudiante TEXT UNIQUE NOT NULL,
    carrera TEXT,
    ciclo TEXT,
    esAsesor INTEGER NOT NULL,
    FOREIGN KEY (id) REFERENCES Usuario(id)
)''')


# Tabla CicloEscolar
cursor.execute('''CREATE TABLE IF NOT EXISTS CicloEscolar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombreOficial TEXT NOT NULL,
    fechaInicio TEXT NOT NULL,
    fechaTermino TEXT NOT NULL,
    estado TEXT NOT NULL
)''')


# Tabla Curso
cursor.execute('''CREATE TABLE IF NOT EXISTS Curso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombreMateria TEXT NOT NULL,
    seccion TEXT NOT NULL,
    descripcion TEXT,
    codigoUnico TEXT UNIQUE NOT NULL,
    estado TEXT NOT NULL,
    tipoEvaluacion TEXT NOT NULL,
    umbralNumerico REAL NOT NULL,
    diasSemana TEXT NOT NULL,
    horarioInicio TEXT NOT NULL,
    horarioFin TEXT NOT NULL,
    cicloEscolar_id INTEGER,
    docente_id INTEGER,
    FOREIGN KEY (cicloEscolar_id) REFERENCES CicloEscolar(id),
    FOREIGN KEY (docente_id) REFERENCES Docente(id)
)''')


# Tabla Matricula
cursor.execute('''CREATE TABLE IF NOT EXISTS Matricula (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fechaInscripcion TEXT NOT NULL,
    estatus TEXT NOT NULL,
    calificacionAcumuladaActual REAL,
    curso_id INTEGER,
    estudiante_id INTEGER,
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (estudiante_id) REFERENCES Estudiante(id)
)''')


# Tabla SesionClase
cursor.execute('''CREATE TABLE IF NOT EXISTS SesionClase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    horarioInicio TEXT NOT NULL,
    horarioFin TEXT NOT NULL,
    tema TEXT,
    listaGuardada INTEGER NOT NULL,
    curso_id INTEGER,
    FOREIGN KEY (curso_id) REFERENCES Curso(id)
)''')


# Tabla Asistencia
cursor.execute('''CREATE TABLE IF NOT EXISTS Asistencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estado TEXT NOT NULL,
    observaciones TEXT,
    sesionClase_id INTEGER,
    matricula_id INTEGER,
    FOREIGN KEY (sesionClase_id) REFERENCES SesionClase(id),
    FOREIGN KEY (matricula_id) REFERENCES Matricula(id)
)''')


# Tabla RegistroRiesgo
cursor.execute('''CREATE TABLE IF NOT EXISTS RegistroRiesgo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semaforo TEXT NOT NULL,
    estatusNormativo TEXT NOT NULL,
    riesgoPorHistorial INTEGER NOT NULL,
    rezagoCritico INTEGER NOT NULL,
    detalleCausaRezago TEXT,
    matricula_id INTEGER,
    FOREIGN KEY (matricula_id) REFERENCES Matricula(id)
)''')


# Tabla CategoriaEvaluacion
cursor.execute('''CREATE TABLE IF NOT EXISTS CategoriaEvaluacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    porcentajePeso REAL NOT NULL,
    curso_id INTEGER,
    FOREIGN KEY (curso_id) REFERENCES Curso(id)
)''')


# Tabla Actividad
cursor.execute('''CREATE TABLE IF NOT EXISTS Actividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    fechaHoraLimite TEXT NOT NULL,
    puntuacionMaxima REAL NOT NULL,
    categoriaEvaluacion_id INTEGER,
    FOREIGN KEY (categoriaEvaluacion_id) REFERENCES CategoriaEvaluacion(id)
)''')


# Tabla Entrega
cursor.execute('''CREATE TABLE IF NOT EXISTS Entrega (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fechaHoraEntrega TEXT NOT NULL,
    archivoDigital TEXT,
    entregadoConRetraso INTEGER NOT NULL,
    actividad_id INTEGER,
    matricula_id INTEGER,
    FOREIGN KEY (actividad_id) REFERENCES Actividad(id),
    FOREIGN KEY (matricula_id) REFERENCES Matricula(id)
)''')


# Tabla Calificacion
cursor.execute('''CREATE TABLE IF NOT EXISTS Calificacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calificacionObtenida REAL NOT NULL,
    retroalimentacion TEXT,
    fecha TEXT NOT NULL,
    entrega_id INTEGER,
    FOREIGN KEY (entrega_id) REFERENCES Entrega(id)
)''')


# Tabla PublicacionAsesoria
cursor.execute('''CREATE TABLE IF NOT EXISTS PublicacionAsesoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    materia TEXT NOT NULL,
    horario TEXT NOT NULL,
    modalidad TEXT NOT NULL,
    lugarOMedio TEXT NOT NULL,
    topico TEXT,
    estado TEXT NOT NULL,
    estudiante_id INTEGER,
    FOREIGN KEY (estudiante_id) REFERENCES Estudiante(id)
)''')


# Tabla BibliotecaNormatividad
cursor.execute('''CREATE TABLE IF NOT EXISTS BibliotecaNormatividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extractosReglamento TEXT,
    guiaSIATCE TEXT,
    directorioCoordinacion TEXT,
    checklistSupervivencia TEXT
)''')

conexion.commit()
conexion.close()

print("¡Estructura de la base de datos actualizada exitosamente!")