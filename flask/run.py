from flask import Flask, jsonify, render_template_string, request
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import pyodbc
from passlib.hash import bcrypt
import json

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "clave_super_secreta_de_prueba"
jwt = JWTManager(app)

# Conexión a SQL Server
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=sqlserver;"
    "DATABASE=SysPresta;"
    "UID=sa;"
    "PWD=yourStrong(!)Password;"
    "TrustServerCertificate=yes;"
)

# HTML con formulario y cambio dinámico de texto en botones
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>SysPresta Login</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            font-family: Arial, sans-serif;
            background-color: #f0f2f5;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-box {
            background: white;
            padding: 30px 40px;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(0,0,0,0.1);
            width: 300px;
            text-align: center;
        }
        .login-box h1 {
            margin-bottom: 20px;
            font-size: 24px;
            color: #333;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            box-sizing: border-box;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            font-size: 14px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        #nombre {
            display: none;
        }
        #loginResult {
            margin-top: 15px;
            font-size: 13px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>SysPresta</h1>
        <input type="text" id="nombre" placeholder="Nombre" />
        <input type="email" id="correo" placeholder="Correo" />
        <input type="password" id="contrasena" placeholder="Contraseña" />
        <button id="btnLogin" onclick="login()">Ingresar</button>
        <button id="btnRegistrar" onclick="toggleRegistrar()">Registrar</button>
        <div id="loginResult"></div>
    </div>

    <script>
        let modoRegistro = false;
        let token = null;

        function login() {
            const correo = document.getElementById('correo').value;
            const contrasena = document.getElementById('contrasena').value;

            if (!modoRegistro) {
                fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ correo, contrasena })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.access_token) {
                        token = data.access_token;
                        window.location.href = data.redirect_url + "?token=" + token;
                    } else {
                        document.getElementById('loginResult').innerText =
                            data.msg || 'Error al iniciar sesión';
                    }
                }).catch(() => {
                    document.getElementById('loginResult').innerText = 'Error en la conexión';
                });
            } else {
                const nombre = document.getElementById('nombre').value;
                if (!nombre || !correo || !contrasena) {
                    document.getElementById('loginResult').innerText = "Completa todos los campos";
                    return;
                }

                fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre, correo, contrasena })
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('loginResult').innerText = data.msg || data.message;
                    if (data.msg && data.msg.includes("exitosamente")) {
                        toggleRegistrar(); // volver al modo login
                    }
                }).catch(() => {
                    document.getElementById('loginResult').innerText = 'Error en la conexión';
                });
            }
        }

        function toggleRegistrar() {
            const nombreField = document.getElementById('nombre');
            const btnLogin = document.getElementById('btnLogin');
            const btnRegistrar = document.getElementById('btnRegistrar');

            modoRegistro = !modoRegistro;

            if (modoRegistro) {
                nombreField.style.display = 'block';
                btnLogin.innerText = 'Ingresar usuario';
                btnRegistrar.innerText = 'Cancelar';
            } else {
                nombreField.style.display = 'none';
                btnLogin.innerText = 'Ingresar';
                btnRegistrar.innerText = 'Registrar';
                document.getElementById('loginResult').innerText = "";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(html_template)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nombre = data.get('nombre')
    correo = data.get('correo')
    contrasena = data.get('contrasena')
    rol = 'usuario'

    if not all([nombre, correo, contrasena]):
        return jsonify({"msg": "Faltan datos"}), 400

    hashed_password = bcrypt.hash(contrasena)

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT UsuarioID FROM Usuarios WHERE Correo = ?", (correo,))
        if cursor.fetchone():
            return jsonify({"msg": "Correo ya registrado"}), 409

        cursor.execute("""
            INSERT INTO Usuarios (Nombre, Correo, Contrasena, Rol)
            VALUES (?, ?, ?, ?)
        """, (nombre, correo, hashed_password, rol))
        conn.commit()
        return jsonify({"msg": "Usuario registrado exitosamente"}), 201
    except Exception as e:
        return jsonify({"msg": "Error en la base de datos", "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    if not all([correo, contrasena]):
        return jsonify({"msg": "Faltan datos"}), 400

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT UsuarioID, Contrasena, Rol FROM Usuarios WHERE Correo = ?", (correo,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"msg": "Correo o contraseña incorrectos"}), 401

        usuario_id, hashed_pass, rol = user

        if not bcrypt.verify(contrasena, hashed_pass):
            return jsonify({"msg": "Correo o contraseña incorrectos"}), 401

        identity = json.dumps({"id": usuario_id})
        access_token = create_access_token(identity=identity)

        destino = "http://localhost:8082/admin" if rol == "admin" else "http://localhost:8082/usuario"
        return jsonify(access_token=access_token, rol=rol, redirect_url=destino)
    except Exception as e:
        return jsonify({"msg": "Error en la base de datos", "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    identity = get_jwt_identity()
    return jsonify({"usuario": identity})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
