from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, decode_token
import pyodbc
import json
from datetime import datetime

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "clave_super_secreta_de_prueba"
jwt = JWTManager(app)

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=sqlserver;"
    "DATABASE=SysPresta;"
    "UID=sa;"
    "PWD=yourStrong(!)Password;"
    "TrustServerCertificate=yes;"
)

def obtener_usuario(usuario_id):
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Nombre, Rol FROM Usuarios WHERE UsuarioID = ?", (usuario_id,))
        row = cursor.fetchone()
        return (row.Nombre, row.Rol) if row else (None, None)

@app.route('/usuario')
def usuario_page():
    try:
        token = request.args.get('token')
        if not token:
            return "Token no proporcionado", 401

        identity = json.loads(decode_token(token)["sub"])
        usuario_id = identity["id"]

        nombre, rol = obtener_usuario(usuario_id)
        if not nombre or rol != "usuario":
            return "Acceso denegado", 403

        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT p.PrestamoID, p.FechaInicio, e.EquipoID, e.Nombre AS EquipoNombre, e.Tipo
                FROM Prestamos p
                JOIN DetallePrestamoEquipos dpe ON p.PrestamoID = dpe.PrestamoID
                JOIN Equipos e ON dpe.EquipoID = e.EquipoID
                WHERE p.UsuarioID = ? AND p.Estado = 'Activo'
            """, (usuario_id,))
            prestamos_activos_equipos = cursor.fetchall()

            cursor.execute("""
                SELECT p.PrestamoID, p.FechaInicio, es.EspacioID, es.Nombre AS EspacioNombre, es.Ubicacion
                FROM Prestamos p
                JOIN DetallePrestamoEspacios dpe ON p.PrestamoID = dpe.PrestamoID
                JOIN Espacios es ON dpe.EspacioID = es.EspacioID
                WHERE p.UsuarioID = ? AND p.Estado = 'Activo'
            """, (usuario_id,))
            prestamos_activos_espacios = cursor.fetchall()

            cursor.execute("""
                SELECT PrestamoID, FechaInicio, FechaFin, Estado
                FROM Prestamos
                WHERE UsuarioID = ? AND Estado = 'Finalizado'
                ORDER BY FechaFin DESC
            """, (usuario_id,))
            prestamos_finalizados = cursor.fetchall()

            historial_detalles = {}
            for p in prestamos_finalizados:
                pid = p.PrestamoID
                cursor.execute("""
                    SELECT e.Nombre FROM DetallePrestamoEquipos dpe
                    JOIN Equipos e ON dpe.EquipoID = e.EquipoID
                    WHERE dpe.PrestamoID = ?
                """, (pid,))
                equipos = [row.Nombre for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT es.Nombre FROM DetallePrestamoEspacios dpe
                    JOIN Espacios es ON dpe.EspacioID = es.EspacioID
                    WHERE dpe.PrestamoID = ?
                """, (pid,))
                espacios = [row.Nombre for row in cursor.fetchall()]
                historial_detalles[pid] = {'equipos': equipos, 'espacios': espacios}

            cursor.execute("SELECT EquipoID, Nombre, Tipo FROM Equipos WHERE Estado = 'Disponible'")
            equipos_disponibles = cursor.fetchall()
            cursor.execute("SELECT EspacioID, Nombre, Ubicacion FROM Espacios WHERE Estado = 'Disponible'")
            espacios_disponibles = cursor.fetchall()

        html = f"""<!DOCTYPE html>
<html><head><title>Panel Usuario - SysPresta</title>
<style>
body {{ font-family: Arial,sans-serif; background:#f4f4f4; padding:30px; }}
h1 {{ color:#333; }}
.tabs {{ margin-bottom:20px; }}
.tab {{ display:inline-block; margin-right:10px; padding:10px 20px; background:#007bff; color:#fff; cursor:pointer; border-radius:5px; }}
.tab:hover {{ background:#0056b3; }}
.content {{ display:none; background:#fff; padding:20px; border-radius:5px; box-shadow:0 0 10px rgba(0,0,0,0.1); }}
.active {{ display:block; }}
table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
th,td {{ border:1px solid #ccc; padding:8px; text-align:left; }}
th {{ background:#007bff; color:#fff; }}
tr:nth-child(even) {{ background:#f2f2f2; }}
button {{ padding:6px 12px; background:#28a745; color:#fff; border:none; border-radius:4px; cursor:pointer; }}
button:hover {{ background:#218838; }}
</style>
<script>
const token = new URLSearchParams(window.location.search).get('token');
function showTab(id) {{
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
    document.getElementById(id).classList.add('active');
}}
function pedirPrestado(tipo,id) {{
    if(!confirm('¿Deseas pedir prestado este '+tipo+'?')) return;
    fetch('/api/pedir_prestado?token='+encodeURIComponent(token), {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{tipo:tipo,id:id}})
    }}).then(r=>r.json()).then(data=>{{
        if(data.error) alert('Error: '+data.error);
        else {{ alert('Préstamo creado exitosamente'); location.reload(); }}
    }}).catch(()=>alert('Error de conexión'));
}}
</script>
</head><body>
<h1>Bienvenid@ usuario {nombre}</h1>
<div class="tabs">
<div class="tab" onclick="showTab('activos')">Préstamos Activos</div>
<div class="tab" onclick="showTab('historial')">Historial de Préstamos</div>
<div class="tab" onclick="showTab('disponibilidad')">Disponibilidad</div>
</div>

<div id="activos" class="content active">
<h2>Equipos Prestados Activos</h2>"""

        if prestamos_activos_equipos:
            html += "<table><tr><th>Nombre</th><th>Tipo</th><th>Fecha de préstamo</th></tr>"
            for p in prestamos_activos_equipos:
                fecha = p.FechaInicio.strftime("%Y-%m-%d") if p.FechaInicio else "N/A"
                nombre_eq = p.EquipoNombre if p.EquipoNombre else "-"
                tipo_eq = p.Tipo if p.Tipo else "-"
                html += f"<tr><td>{nombre_eq}</td><td>{tipo_eq}</td><td>{fecha}</td></tr>"
            html += "</table>"
        else:
            html += "<p>No tienes equipos prestados activos.</p>"

        html += "<h2>Espacios Prestados Activos</h2>"

        if prestamos_activos_espacios:
            html += "<table><tr><th>Nombre</th><th>Ubicación</th><th>Fecha de préstamo</th></tr>"
            for p in prestamos_activos_espacios:
                fecha = p.FechaInicio.strftime("%Y-%m-%d") if p.FechaInicio else "N/A"
                nombre_es = p.EspacioNombre if p.EspacioNombre else "-"
                ubicacion = p.Ubicacion if p.Ubicacion else "-"
                html += f"<tr><td>{nombre_es}</td><td>{ubicacion}</td><td>{fecha}</td></tr>"
            html += "</table>"
        else:
            html += "<p>No tienes espacios prestados activos.</p>"

        html += "</div><div id='historial' class='content'>"
        html += "<h2>Historial de Préstamos</h2>"

        if prestamos_finalizados:
            html += "<table><tr><th>ID Préstamo</th><th>Fecha Inicio</th><th>Fecha Fin</th></tr>"
            for p in prestamos_finalizados:
                fin = p.FechaFin.strftime("%Y-%m-%d") if p.FechaFin else "-"
                inicio = p.FechaInicio.strftime("%Y-%m-%d") if p.FechaInicio else "-"
                html += f"<tr><td>{p.PrestamoID}</td><td>{inicio}</td><td>{fin}</td></tr>"
            html += "</table>"
        else:
            html += "<p>No hay historial de préstamos.</p>"

        html += "</div><div id='disponibilidad' class='content'>"


        if equipos_disponibles:
            html += "<table><tr><th>Nombre</th><th>Tipo</th><th>Acción</th></tr>"
            for eq in equipos_disponibles:
                html += f"<tr><td>{eq.Nombre}</td><td>{eq.Tipo}</td><td><button onclick=\"pedirPrestado('equipo',{eq.EquipoID})\">Pedir prestado</button></td></tr>"
            html += "</table>"
        else:
            html += "<p>No hay equipos disponibles.</p>"

        html += "<h2>Espacios Disponibles</h2>"

        if espacios_disponibles:
            html += "<table><tr><th>Nombre</th><th>Ubicación</th><th>Acción</th></tr>"
            for es in espacios_disponibles:
                html += f"<tr><td>{es.Nombre}</td><td>{es.Ubicacion}</td><td><button onclick=\"pedirPrestado('espacio',{es.EspacioID})\">Pedir prestado</button></td></tr>"
            html += "</table>"
        else:
            html += "<p>No hay espacios disponibles.</p>"

        html += "</div></body></html>"
        return html

    except Exception as e:
        return f"Error interno: {str(e)}", 500

@app.route('/admin')
def admin_page():
    token = request.args.get('token')
    if not token:
        return "Token no proporcionado", 401
    try:
        identity = json.loads(decode_token(token)["sub"])
        usuario_id = identity["id"]
    except Exception as e:
        return f"Token inválido: {str(e)}", 400

    nombre, rol = obtener_usuario(usuario_id)
    if not nombre or rol != "admin":
        return "Acceso denegado", 403

    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT EquipoID, Nombre, Tipo, Estado, Descripcion FROM Equipos")
        equipos = cursor.fetchall()

        cursor.execute("SELECT EspacioID, Nombre, Ubicacion, Estado FROM Espacios")
        espacios = cursor.fetchall()

        cursor.execute("""
            SELECT u.Nombre AS UsuarioNombre, u.Correo, e.Nombre AS RecursoNombre, 'Equipo' AS TipoRecurso, p.FechaInicio
            FROM Usuarios u
            JOIN Prestamos p ON u.UsuarioID = p.UsuarioID
            JOIN DetallePrestamoEquipos dpe ON p.PrestamoID = dpe.PrestamoID
            JOIN Equipos e ON dpe.EquipoID = e.EquipoID
            WHERE p.Estado = 'Activo' AND e.Estado = 'Ocupado'
        """)
        prestamos_equipos = cursor.fetchall()

        cursor.execute("""
            SELECT u.Nombre AS UsuarioNombre, u.Correo, es.Nombre AS RecursoNombre, 'Espacio' AS TipoRecurso, p.FechaInicio
            FROM Usuarios u
            JOIN Prestamos p ON u.UsuarioID = p.UsuarioID
            JOIN DetallePrestamoEspacios dpe ON p.PrestamoID = dpe.PrestamoID
            JOIN Espacios es ON dpe.EspacioID = es.EspacioID
            WHERE p.Estado = 'Activo' AND es.Estado = 'Ocupado'
        """)
        prestamos_espacios = cursor.fetchall()

        prestamos_activos = prestamos_equipos + prestamos_espacios
        prestamos_activos.sort(key=lambda x: (x.UsuarioNombre, x.FechaInicio))

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Panel Admin - SysPresta</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                padding: 30px;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
            }}
            .tabs {{
                margin-bottom: 20px;
            }}
            .tab {{
                display: inline-block;
                margin-right: 10px;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                cursor: pointer;
                border-radius: 5px;
            }}
            .tab:hover {{
                background-color: #0056b3;
            }}
            .content {{
                display: none;
                background: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            .active {{
                display: block;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                margin-bottom: 40px;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #007bff;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            input[type="checkbox"] {{
                width: 18px;
                height: 18px;
                cursor: pointer;
            }}
        </style>
        <script>
            function showTab(tabId) {{
                document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
            }}

            function cambiarEstado(tipo, id, estado, checkbox) {{
                if (estado === 'Disponible') {{
                    checkbox.checked = true;
                    return;
                }}
                fetch('/api/admin/cambiar_estado', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ tipo: tipo, id: id, nuevo_estado: 'Disponible' }})
                }}).then(resp => resp.json()).then(data => {{
                    if(data.error) {{
                        alert('Error: ' + data.error);
                        checkbox.checked = false;
                    }} else {{
                        alert('Estado cambiado a disponible');
                        location.reload();
                    }}
                }}).catch(() => {{
                    alert('Error de conexión');
                    checkbox.checked = false;
                }});
            }}
        </script>
    </head>
    <body>
        <h1>Bienvenid@ admin {nombre}</h1>
        <div class="tabs">
            <div class="tab" onclick="showTab('equipos')">Equipos</div>
            <div class="tab" onclick="showTab('espacios')">Espacios</div>
            <div class="tab" onclick="showTab('prestamos')">Préstamos Activos</div>
        </div>

        <div id="equipos" class="content active">
            <h2>Equipos</h2>
            <table>
                <tr><th>Nombre</th><th>Tipo</th><th>Descripción</th><th>Disponible</th></tr>
    """
    for eq in equipos:
        checked = "checked" if eq.Estado == "Disponible" else ""
        html += f"""
        <tr>
            <td>{eq.Nombre}</td>
            <td>{eq.Tipo}</td>
            <td>{eq.Descripcion}</td>
            <td><input type="checkbox" {checked} onclick="cambiarEstado('equipo', {eq.EquipoID}, '{eq.Estado}', this)"></td>
        </tr>
        """

    html += """
            </table>
        </div>

        <div id="espacios" class="content">
            <h2>Espacios</h2>
            <table>
                <tr><th>Nombre</th><th>Ubicación</th><th>Disponible</th></tr>
    """
    for es in espacios:
        checked = "checked" if es.Estado == "Disponible" else ""
        html += f"""
        <tr>
            <td>{es.Nombre}</td>
            <td>{es.Ubicacion}</td>
            <td><input type="checkbox" {checked} onclick="cambiarEstado('espacio', {es.EspacioID}, '{es.Estado}', this)"></td>
        </tr>
        """

    html += """
            </table>
        </div>

        <div id="prestamos" class="content">
            <h2>Préstamos Activos</h2>
            <table>
                <tr><th>Usuario</th><th>Correo</th><th>Recurso</th><th>Tipo Recurso</th><th>Fecha Inicio</th></tr>
    """
    for p in prestamos_activos:
        usuario = p.UsuarioNombre
        correo = p.Correo
        recurso = p.RecursoNombre
        tipo_recurso = p.TipoRecurso
        fecha_inicio = p.FechaInicio.strftime("%Y-%m-%d") if p.FechaInicio else "-"
        html += f"""
        <tr>
            <td>{usuario}</td>
            <td>{correo}</td>
            <td>{recurso}</td>
            <td>{tipo_recurso}</td>
            <td>{fecha_inicio}</td>
        </tr>
        """

    html += """
            </table>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/api/admin/cambiar_estado', methods=['POST'])
def cambiar_estado():
    try:
        data = request.get_json()
        tipo = data.get('tipo')
        id_recurso = data.get('id')
        nuevo_estado = data.get('nuevo_estado')

        if tipo not in ('equipo', 'espacio') or id_recurso is None or nuevo_estado != 'Disponible':
            return jsonify({"error": "Datos inválidos"}), 400

        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            if tipo == 'equipo':
                cursor.execute("UPDATE Equipos SET Estado = ? WHERE EquipoID = ?", (nuevo_estado, id_recurso))
                cursor.execute("""
                    SELECT p.PrestamoID FROM Prestamos p
                    JOIN DetallePrestamoEquipos dpe ON p.PrestamoID = dpe.PrestamoID
                    WHERE dpe.EquipoID = ? AND p.Estado = 'Activo'
                """, (id_recurso,))
                prestamos = cursor.fetchall()
                for p in prestamos:
                    prestamo_id = p.PrestamoID
                    cursor.execute("DELETE FROM DetallePrestamoEquipos WHERE PrestamoID = ? AND EquipoID = ?", (prestamo_id, id_recurso))
                    cursor.execute("SELECT COUNT(*) FROM DetallePrestamoEquipos WHERE PrestamoID = ?", (prestamo_id,))
                    count_eq = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM DetallePrestamoEspacios WHERE PrestamoID = ?", (prestamo_id,))
                    count_es = cursor.fetchone()[0]
                    if count_eq == 0 and count_es == 0:
                        fecha_fin = datetime.now()
                        cursor.execute("UPDATE Prestamos SET FechaFin = ?, Estado = 'Finalizado' WHERE PrestamoID = ?", (fecha_fin, prestamo_id))
            else:
                cursor.execute("UPDATE Espacios SET Estado = ? WHERE EspacioID = ?", (nuevo_estado, id_recurso))
                cursor.execute("""
                    SELECT p.PrestamoID FROM Prestamos p
                    JOIN DetallePrestamoEspacios dpe ON p.PrestamoID = dpe.PrestamoID
                    WHERE dpe.EspacioID = ? AND p.Estado = 'Activo'
                """, (id_recurso,))
                prestamos = cursor.fetchall()
                for p in prestamos:
                    prestamo_id = p.PrestamoID
                    cursor.execute("DELETE FROM DetallePrestamoEspacios WHERE PrestamoID = ? AND EspacioID = ?", (prestamo_id, id_recurso))
                    cursor.execute("SELECT COUNT(*) FROM DetallePrestamoEquipos WHERE PrestamoID = ?", (prestamo_id,))
                    count_eq = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM DetallePrestamoEspacios WHERE PrestamoID = ?", (prestamo_id,))
                    count_es = cursor.fetchone()[0]
                    if count_eq == 0 and count_es == 0:
                        fecha_fin = datetime.now()
                        cursor.execute("UPDATE Prestamos SET FechaFin = ?, Estado = 'Finalizado' WHERE PrestamoID = ?", (fecha_fin, prestamo_id))

            conn.commit()

        return jsonify({"msg": "Estado actualizado a disponible"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pedir_prestado', methods=['POST'])
def pedir_prestado():
    try:
        data = request.get_json()
        tipo = data.get('tipo')
        id_recurso = data.get('id')
        token = request.args.get('token')

        if not token:
            return jsonify({"error": "Token no proporcionado"}), 401

        identity = json.loads(decode_token(token)["sub"])
        usuario_id = identity["id"]

        if tipo not in ('equipo', 'espacio') or id_recurso is None:
            return jsonify({"error": "Datos inválidos"}), 400

        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            if tipo == 'equipo':
                cursor.execute("SELECT Estado FROM Equipos WHERE EquipoID = ?", (id_recurso,))
                row = cursor.fetchone()
                if not row or row.Estado != 'Disponible':
                    return jsonify({"error": "Equipo no disponible"}), 400
            else:
                cursor.execute("SELECT Estado FROM Espacios WHERE EspacioID = ?", (id_recurso,))
                row = cursor.fetchone()
                if not row or row.Estado != 'Disponible':
                    return jsonify({"error": "Espacio no disponible"}), 400

            cursor.execute("SELECT PrestamoID FROM Prestamos WHERE UsuarioID = ? AND Estado = 'Activo'", (usuario_id,))
            prestamo = cursor.fetchone()

            if prestamo:
                prestamo_id = prestamo.PrestamoID
            else:
                ahora = datetime.now()
                cursor.execute("""
                    INSERT INTO Prestamos (UsuarioID, FechaInicio, Estado)
                    OUTPUT INSERTED.PrestamoID
                    VALUES (?, ?, 'Activo')
                """, (usuario_id, ahora))
                prestamo_id = cursor.fetchone()[0]
                conn.commit()

            if tipo == 'equipo':
                cursor.execute("INSERT INTO DetallePrestamoEquipos (PrestamoID, EquipoID) VALUES (?, ?)", (prestamo_id, id_recurso))
                cursor.execute("UPDATE Equipos SET Estado = 'Ocupado' WHERE EquipoID = ?", (id_recurso,))
            else:
                cursor.execute("INSERT INTO DetallePrestamoEspacios (PrestamoID, EspacioID) VALUES (?, ?)", (prestamo_id, id_recurso))
                cursor.execute("UPDATE Espacios SET Estado = 'Ocupado' WHERE EspacioID = ?", (id_recurso,))

            conn.commit()

        return jsonify({"msg": "Préstamo creado exitosamente"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=True)
