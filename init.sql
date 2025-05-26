-- Crear base de datos (opcional si no la has creado desde la interfaz)
CREATE DATABASE SysPresta;
GO

USE SysPresta;
GO

-- Tabla de Usuarios
CREATE TABLE Usuarios (
    UsuarioID INT PRIMARY KEY IDENTITY(1,1),
    Nombre NVARCHAR(100) NOT NULL,
    Correo NVARCHAR(100) UNIQUE NOT NULL,
    Contrasena NVARCHAR(100) NOT NULL,
    Rol NVARCHAR(50) NOT NULL, -- 'admin' o 'usuario'
    FechaRegistro DATETIME DEFAULT GETDATE()
);

-- Tabla de Equipos
CREATE TABLE Equipos (
    EquipoID INT PRIMARY KEY IDENTITY(1,1),
    Nombre NVARCHAR(100) NOT NULL,
    Tipo NVARCHAR(50),
    Estado NVARCHAR(50) DEFAULT 'Disponible', -- Disponible, Prestado, En Reparación
    Descripcion NVARCHAR(255)
);

-- Tabla de Espacios
CREATE TABLE Espacios (
    EspacioID INT PRIMARY KEY IDENTITY(1,1),
    Nombre NVARCHAR(100) NOT NULL,
    Ubicacion NVARCHAR(100),
    Capacidad INT,
    Estado NVARCHAR(50) DEFAULT 'Disponible'
);

-- Tabla de Préstamos
CREATE TABLE Prestamos (
    PrestamoID INT PRIMARY KEY IDENTITY(1,1),
    UsuarioID INT,
    FechaInicio DATETIME NOT NULL,
    FechaFin DATETIME,
    Estado NVARCHAR(50) DEFAULT 'Activo', -- Activo, Finalizado, Cancelado
    FOREIGN KEY (UsuarioID) REFERENCES Usuarios(UsuarioID)
);

-- Detalle del préstamo - Equipos
CREATE TABLE DetallePrestamoEquipos (
    DetalleID INT PRIMARY KEY IDENTITY(1,1),
    PrestamoID INT,
    EquipoID INT,
    FOREIGN KEY (PrestamoID) REFERENCES Prestamos(PrestamoID),
    FOREIGN KEY (EquipoID) REFERENCES Equipos(EquipoID)
);

-- Detalle del préstamo - Espacios
CREATE TABLE DetallePrestamoEspacios (
    DetalleID INT PRIMARY KEY IDENTITY(1,1),
    PrestamoID INT,
    EspacioID INT,
    FOREIGN KEY (PrestamoID) REFERENCES Prestamos(PrestamoID),
    FOREIGN KEY (EspacioID) REFERENCES Espacios(EspacioID)
);

-- Tabla de Auditoría
CREATE TABLE Auditoria (
    LogID INT PRIMARY KEY IDENTITY(1,1),
    UsuarioID INT,
    Accion NVARCHAR(100),
    Descripcion NVARCHAR(255),
    Fecha DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (UsuarioID) REFERENCES Usuarios(UsuarioID)
);

-- Inserciones de ejemplo con contraseñas bcrypt
-- Contraseñas: 1234 (Ana), abcd (Luis)
-- Hash generados con passlib.hash.bcrypt.hash()

INSERT INTO Usuarios (Nombre, Correo, Contrasena, Rol)
VALUES 
('Ana Torres', 'ana@example.com', '$2b$12$D7DRJ3Xl3n4Y.09VDU8Cj.0er7zIgViZOWG9McCc1UtEMIRHFMZmq', 'admin'),
('Luis Pérez', 'luis@example.com', '$2b$12$hrFz9E2e2Ey.Yw8DLfTQ0uxDd1cgA5OtwEcb5YVBApYk8w8CSDXxC', 'usuario');

-- Equipos
INSERT INTO Equipos (Nombre, Tipo, Estado, Descripcion)
VALUES 
('Laptop Dell', 'Laptop', 'Disponible', 'Dell Inspiron 15'),
('Proyector Epson', 'Proyector', 'Disponible', 'Epson XGA 3200'),
('Teclado mecánico Logitech', 'Teclado', 'Disponible', 'Logitech G Pro X'),
('Cámara Sony', 'Cámara', 'Disponible', 'Sony Alpha 7 III'),
('Servidor Dell', 'Servidor', 'Disponible', 'Dell PowerEdge R740');

-- Espacios
INSERT INTO Espacios (Nombre, Ubicacion, Capacidad)
VALUES 
('Sala de Reuniones A', 'Edificio 1', 10),
('Cubículo 3', 'Biblioteca', 1);

-- Préstamo (Luis Pérez, UsuarioID = 2)
INSERT INTO Prestamos (UsuarioID, FechaInicio)
VALUES (2, GETDATE());

-- Detalles del préstamo
INSERT INTO DetallePrestamoEquipos (PrestamoID, EquipoID)
VALUES (1, 1);

INSERT INTO DetallePrestamoEspacios (PrestamoID, EspacioID)
VALUES (1, 1);



-- Consultas para verificar datos
SELECT * FROM Usuarios;
SELECT * FROM Equipos;
SELECT * FROM Espacios;
SELECT * FROM Prestamos;
SELECT * FROM DetallePrestamoEquipos;
SELECT * FROM DetallePrestamoEspacios;

DELETE FROM Prestamos
WHERE UsuarioID IS NULL OR UsuarioID = 5;

UPDATE Usuarios
SET Rol = 'admin'
WHERE Correo = 'sebas@mail.com';
GO

-- Actualizar contraseña de Luis Pérez
UPDATE Usuarios
SET Contrasena = '$2b$12$BF39kRabiiK0xizXuHZfKO4a8O.kSOP2sXJUd79UkSBebDia3hDNC'
WHERE Correo = 'luis@example.com';
GO


-- Actualizar estado del equipo a 'Ocupado'
UPDATE Equipos
SET Estado = 'Ocupado'
WHERE EquipoID = 1;

-- Actualizar estado del espacio a 'Ocupado'
UPDATE Espacios
SET Estado = 'Ocupado'
WHERE EspacioID = 1;

SELECT * FROM DetallePrestamoEquipos;
SELECT * FROM DetallePrestamoEspacios;

Delete Prestamos where PrestamoID = 1002