from flask import Flask, render_template,request,redirect,url_for,session,flash,jsonify
from datetime import datetime
import sqlite3
import os


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'basededatosflask.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'proveedor_facturas')
ALLOWED_EXTENSIONS = {'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_has_column(conn, table_name, column_name):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(col[1] == column_name for col in cols)


def initialize_database():
    """Crea el esquema limpio para aislamiento total por usuario."""
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                rol TEXT DEFAULT 'usuario'
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT,
                telefono TEXT,
                direccion TEXT,
                id_usuario INTEGER NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                razon_social TEXT,
                nombre_comercial TEXT,
                cuit TEXT,
                telefono TEXT,
                email TEXT,
                direccion_fiscal TEXT,
                calle_numero TEXT,
                ciudad TEXT,
                provincia TEXT,
                codigo_postal TEXT,
                pais TEXT,
                contacto TEXT,
                condicion_pago TEXT,
                estado TEXT DEFAULT 'activo',
                created_at TEXT,
                updated_at TEXT,
                id_usuario INTEGER NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                precio REAL,
                stock INTEGER DEFAULT 0,
                precio_costo REAL,
                margen_ganancia REAL,
                codigo_barras TEXT,
                id_usuario INTEGER NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS facturas (
                id_factura INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente INTEGER,
                fecha TEXT,
                total REAL DEFAULT 0,
                id_usuario INTEGER NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS detalle_factura (
                id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
                id_factura INTEGER NOT NULL,
                id_producto INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL,
                subtotal REAL,
                metodo_pago TEXT,
                id_usuario INTEGER NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS facturas_proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_proveedor INTEGER NOT NULL,
                numero TEXT,
                fecha TEXT,
                monto REAL,
                descripcion TEXT,
                archivo TEXT,
                creado_en TEXT,
                id_usuario INTEGER NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS cajas (
                id_caja INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_apertura TEXT NOT NULL,
                usuario TEXT,
                monto_apertura REAL NOT NULL,
                monto_cierre REAL,
                fecha_cierre TEXT,
                estado TEXT NOT NULL,
                id_usuario INTEGER NOT NULL
            )
        ''')

        for table_name, column_name in [
            ("detalle_factura", "metodo_pago"),
            ("productos", "codigo_barras"),
            ("clientes", "id_usuario"),
            ("proveedores", "id_usuario"),
            ("facturas", "id_usuario"),
            ("cajas", "id_usuario"),
            ("facturas_proveedores", "id_usuario"),
        ]:
            if not table_has_column(conn, table_name, column_name):
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER")

        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_codigo_barras_usuario ON productos(id_usuario, codigo_barras)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_clientes_usuario ON clientes(id_usuario)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_proveedores_usuario ON proveedores(id_usuario)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_productos_usuario ON productos(id_usuario)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_facturas_usuario ON facturas(id_usuario)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_detalle_factura_usuario ON detalle_factura(id_usuario)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_facturas_proveedores_usuario ON facturas_proveedores(id_usuario)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_cajas_usuario ON cajas(id_usuario)')

        conn.commit()
    finally:
        conn.close()


initialize_database()


def get_current_user_id():
    user_id = session.get("user_id")
    if user_id is not None:
        return user_id

    nombre = session.get("user")
    if not nombre:
        return None

    conn = get_db_connection()
    try:
        user = conn.execute("SELECT id FROM usuarios WHERE nombre = ?", (nombre,)).fetchone()
        if user:
            session["user_id"] = user["id"]
            return user["id"]
    except Exception:
        pass
    finally:
        conn.close()

    return None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/productos/search', methods=['GET'])
def api_productos_search():
    q = request.args.get('q', '').strip()
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        if user_id is None:
            productos = []
        elif q:
            rows = conn.execute("SELECT id_producto, descripcion, precio, stock, codigo_barras FROM productos WHERE id_usuario = ? AND descripcion LIKE ? AND stock > 0 LIMIT 20", (user_id, '%'+q+'%',)).fetchall()
            productos = [dict(r) for r in rows]
        else:
            rows = conn.execute("SELECT id_producto, descripcion, precio, stock, codigo_barras FROM productos WHERE id_usuario = ? AND stock > 0 LIMIT 20", (user_id,)).fetchall()
            productos = [dict(r) for r in rows]
    except Exception as e:
        productos = []
        print(f"Error en api_productos_search: {e}")
    finally:
        conn.close()

    return jsonify(productos)


@app.route('/api/productos/by_codigo/<codigo>', methods=['GET'])
def api_productos_by_codigo(codigo):
    codigo = codigo.strip()
    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        if user_id is None:
            return jsonify({'error': 'not found'}), 404
        row = conn.execute("SELECT id_producto, descripcion, precio, stock, codigo_barras FROM productos WHERE id_usuario = ? AND codigo_barras = ?", (user_id, codigo)).fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        producto = dict(row)
    except Exception as e:
        print(f"Error en api_productos_by_codigo: {e}")
        return jsonify({'error': 'server error'}), 500
    finally:
        conn.close()

    return jsonify(producto)

#----------------------------------------------------- Funciones dashboard ------------------------------------------------------
def get_dashboard_data():
    """Obtiene datos reales para el dashboard del usuario logueado."""
    user_id = get_current_user_id()
    conn = get_db_connection()

    stats = {
        'ventas_hoy': 0,
        'total_dia': 0,
        'productos_stock': 0,
        'stock_bajo': 0,
        'total_clientes': 0
    }

    try:
        if user_id is None:
            return stats

        stats['total_clientes'] = conn.execute('SELECT COUNT(*) as count FROM clientes WHERE id_usuario = ?', (user_id,)).fetchone()['count']

        stats['productos_stock'] = conn.execute('SELECT COUNT(*) as count FROM productos WHERE id_usuario = ? AND stock > 0', (user_id,)).fetchone()['count']
        stats['stock_bajo'] = conn.execute('SELECT COUNT(*) as count FROM productos WHERE id_usuario = ? AND stock <= 5 AND stock > 0', (user_id,)).fetchone()['count']

        hoy = datetime.now().strftime("%Y-%m-%d")
        stats['ventas_hoy'] = conn.execute('SELECT COUNT(*) as count FROM facturas WHERE id_usuario = ? AND DATE(fecha) = ?', (user_id, hoy)).fetchone()['count']
        stats['total_dia'] = conn.execute('SELECT SUM(total) as total FROM facturas WHERE id_usuario = ? AND DATE(fecha) = ?', (user_id, hoy)).fetchone()['total']
        if stats['total_dia'] is None:
            stats['total_dia'] = 0
        else:
            stats['total_dia'] = round(stats['total_dia'], 2)

    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
    finally:
        conn.close()

    return stats


def get_productos_stock_bajo():
    """Obtiene productos con stock bajo del usuario actual."""
    user_id = get_current_user_id()
    conn = get_db_connection()
    productos = []

    try:
        if user_id is None:
            return productos

        query = '''
        SELECT descripcion, stock, 5 as stock_minimo,
               CASE 
                   WHEN stock <= 2 THEN 'Crítico'
                   WHEN stock <= 5 THEN 'Bajo'
                   ELSE 'Normal'
               END as estado
        FROM productos 
        WHERE id_usuario = ? AND stock <= 5
        ORDER BY stock ASC
        LIMIT 10
        '''
        productos = conn.execute(query, (user_id,)).fetchall()
    except Exception as e:
        print(f"Error obteniendo productos con stock bajo: {e}")
        productos = []
    finally:
        conn.close()

    return productos



#----------------------------------------------------- Autenticacion ------------------------------------------------------

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]
        rol = "usuario"

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
                (nombre, email, password, rol)
            )
            conn.commit()
            flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("El correo electrónico ya está registrado.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user"] = user["nombre"]
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        else:
            flash("Email o contraseña incorrectos.", "danger")

    return render_template("login.html")

#----------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------- Dashboard ------------------------------------------------------
@app.route('/dashboard',methods=['GET'])
def dashboard():
    if "user" in session:
        stats = get_dashboard_data()
        productos_stock_bajo = get_productos_stock_bajo()
        return render_template("dashboard.html",
                               nombre=session["user"],
                               stats=stats,
                               productos_stock_bajo=productos_stock_bajo)
    else:
        flash("Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for("login"))
#----------------------------------------------------- Proveedores ------------------------------------------------------
# ...existing code...
@app.route('/dashboard/proveedores', methods=['GET', 'POST'])
def gestion_proveedores():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    proveedores_rows = conn.execute('SELECT * FROM proveedores WHERE id_usuario = ? ORDER BY razon_social', (user_id,)).fetchall()
    proveedores = [dict(p) for p in proveedores_rows]

    if request.method == 'POST':
        pid = request.form.get('id')
        razon_social = request.form.get('razon_social', '').strip()
        nombre_comercial = request.form.get('nombre_comercial', '').strip()
        cuit = request.form.get('cuit', '').strip()
        telefono = request.form.get('telefono', '').strip()
        email = request.form.get('email', '').strip()
        direccion_fiscal = request.form.get('direccion_fiscal', '').strip()
        calle_numero = request.form.get('calle_numero', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        provincia = request.form.get('provincia', '').strip()
        codigo_postal = request.form.get('codigo_postal', '').strip()
        pais = request.form.get('pais', '').strip()
        contacto = request.form.get('contacto', '').strip()
        condicion_pago = request.form.get('condicion_pago', '').strip()
        estado = request.form.get('estado', 'activo').strip()

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            if pid:
                conn.execute("""
                    UPDATE proveedores SET
                        razon_social = ?, nombre_comercial = ?, cuit = ?, telefono = ?, email = ?,
                        direccion_fiscal = ?, calle_numero = ?, ciudad = ?, provincia = ?, codigo_postal = ?,
                        pais = ?, contacto = ?, condicion_pago = ?, estado = ?, updated_at = ?
                    WHERE id = ? AND id_usuario = ?
                """, (
                    razon_social, nombre_comercial, cuit, telefono, email,
                    direccion_fiscal, calle_numero, ciudad, provincia, codigo_postal,
                    pais, contacto, condicion_pago, estado, now, pid, user_id
                ))
                flash('Proveedor actualizado exitosamente', 'success')
            else:
                conn.execute("""
                    INSERT INTO proveedores (
                        razon_social, nombre_comercial, cuit, telefono, email,
                        direccion_fiscal, calle_numero, ciudad, provincia, codigo_postal,
                        pais, contacto, condicion_pago, estado, created_at, updated_at, id_usuario
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    razon_social, nombre_comercial, cuit, telefono, email,
                    direccion_fiscal, calle_numero, ciudad, provincia, codigo_postal,
                    pais, contacto, condicion_pago, estado, now, now, user_id
                ))
                flash('Proveedor agregado exitosamente', 'success')
            conn.commit()
        except Exception as e:
            conn.rollback()
            flash(f'Error al guardar proveedor: {e}', 'danger')
        finally:
            proveedores_rows = conn.execute('SELECT * FROM proveedores WHERE id_usuario = ? ORDER BY razon_social', (user_id,)).fetchall()
            proveedores = [dict(p) for p in proveedores_rows]

    conn.close()
    return render_template('gestion_proveedores.html', proveedores=proveedores)


@app.route('/dashboard/proveedores/<int:id>/facturas', methods=['GET', 'POST'])
def proveedor_facturas(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    proveedor = conn.execute('SELECT * FROM proveedores WHERE id = ? AND id_usuario = ?', (id, user_id)).fetchone()
    if not proveedor:
        conn.close()
        flash('Proveedor no encontrado', 'danger')
        return redirect(url_for('gestion_proveedores'))

    if request.method == 'POST':
        numero = request.form.get('numero', '').strip()
        fecha = request.form.get('fecha', '').strip()
        monto = request.form.get('monto', '').strip()
        descripcion = request.form.get('descripcion', '').strip()

        archivo = None
        if 'archivo' in request.files:
            file = request.files['archivo']
            if file and file.filename != '' and allowed_file(file.filename):
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"prov_{id}_{timestamp}.pdf"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                archivo = filename
            elif file and file.filename != '':
                flash('Formato de archivo no permitido. Solo PDF.', 'danger')
                conn.close()
                return redirect(url_for('proveedor_facturas', id=id))

        try:
            monto_val = float(monto) if monto else None
        except:
            monto_val = None

        creado_en = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            conn.execute('''INSERT INTO facturas_proveedores (id_proveedor, numero, fecha, monto, descripcion, archivo, creado_en, id_usuario)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (id, numero if numero else None, fecha if fecha else None, monto_val, descripcion if descripcion else None, archivo, creado_en, user_id))
            conn.commit()
            flash('Factura registrada correctamente.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al registrar la factura: {e}', 'danger')

    facturas = conn.execute('SELECT * FROM facturas_proveedores WHERE id_proveedor = ? AND id_usuario = ? ORDER BY creado_en DESC', (id, user_id)).fetchall()
    conn.close()
    return render_template('proveedor_facturas.html', proveedor=proveedor, facturas=facturas)


@app.route('/dashboard/proveedores/facturas/descargar/<int:id>', methods=['GET'])
def descargar_factura(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    f = conn.execute('SELECT archivo FROM facturas_proveedores WHERE id = ? AND id_usuario = ?', (id, user_id)).fetchone()
    conn.close()
    if not f or not f['archivo']:
        flash('Archivo no disponible', 'danger')
        return redirect(request.referrer or url_for('gestion_proveedores'))

    return redirect(url_for('static', filename=f"uploads/proveedor_facturas/{f['archivo']}"))


@app.route('/dashboard/proveedores/facturas/eliminar/<int:id>', methods=['POST'])
def eliminar_factura_proveedor(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    f = conn.execute('SELECT archivo, id_proveedor FROM facturas_proveedores WHERE id = ? AND id_usuario = ?', (id, user_id)).fetchone()
    if not f:
        conn.close()
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('gestion_proveedores'))

    try:
        if f['archivo']:
            path = os.path.join(app.config['UPLOAD_FOLDER'], f['archivo'])
            if os.path.exists(path):
                os.remove(path)

        conn.execute('DELETE FROM facturas_proveedores WHERE id = ? AND id_usuario = ?', (id, user_id))
        conn.commit()
        flash('Factura eliminada correctamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al eliminar factura: {e}', 'danger')
    finally:
        proveedor_id = f['id_proveedor']
        conn.close()

    return redirect(url_for('proveedor_facturas', id=proveedor_id))


@app.route('/dashboard/proveedores/facturas/editar/<int:id>', methods=['POST'])
def editar_factura_proveedor(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    f = conn.execute('SELECT * FROM facturas_proveedores WHERE id = ? AND id_usuario = ?', (id, user_id)).fetchone()
    if not f:
        conn.close()
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('gestion_proveedores'))

    numero = request.form.get('numero', '').strip()
    fecha = request.form.get('fecha', '').strip()
    monto = request.form.get('monto', '').strip()
    descripcion = request.form.get('descripcion', '').strip()

    archivo = f['archivo']
    if 'archivo' in request.files:
        file = request.files['archivo']
        if file and file.filename != '' and allowed_file(file.filename):
            if archivo:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], archivo)
                if os.path.exists(old_path):
                    os.remove(old_path)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"prov_{f['id_proveedor']}_{timestamp}.pdf"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            archivo = filename
        elif file and file.filename != '':
            flash('Formato de archivo no permitido. Solo PDF.', 'danger')
            conn.close()
            return redirect(url_for('proveedor_facturas', id=f['id_proveedor']))

    try:
        monto_val = float(monto) if monto else None
    except:
        monto_val = None

    try:
        conn.execute('''UPDATE facturas_proveedores SET numero = ?, fecha = ?, monto = ?, descripcion = ?, archivo = ? WHERE id = ? AND id_usuario = ?''',
                     (numero if numero else None, fecha if fecha else None, monto_val, descripcion if descripcion else None, archivo, id, user_id))
        conn.commit()
        flash('Factura actualizada correctamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al actualizar factura: {e}', 'danger')
    finally:
        proveedor_id = f['id_proveedor']
        conn.close()

    return redirect(url_for('proveedor_facturas', id=proveedor_id))


@app.route('/proveedores/eliminar/<int:id>', methods=['POST'])
def eliminar_proveedor(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM proveedores WHERE id = ? AND id_usuario = ?", (id, user_id))
        conn.commit()
        flash("Proveedor eliminado correctamente", "danger")
    except Exception as e:
        conn.rollback()
        flash(f"Error al eliminar proveedor: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('gestion_proveedores'))
# ...existing code...

#----------------------------------------------------- --- ------------------------------------------------------



#----------------------------------------------------- Clientes ------------------------------------------------------

@app.route('/dashboard/clientes', methods=['GET'])
def gestion_clientes():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    clientes = conn.execute('SELECT * FROM clientes WHERE id_usuario = ? ORDER BY nombre', (user_id,)).fetchall()
    conn.close()
    return render_template('gestion_clientes.html', clientes=clientes)

@app.route('/dashboard/clientes/agregar_clientes', methods=['GET', 'POST'])
def agregar_clientes():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    if request.method == 'POST':
        user_id = get_current_user_id()
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']

        conn = get_db_connection()
        conn.execute('INSERT INTO clientes (nombre, email, telefono, direccion, id_usuario) VALUES (?, ?, ?, ?, ?)',
                     (nombre, email, telefono, direccion, user_id))
        conn.commit()
        conn.close()
        flash('Cliente agregado exitosamente', 'success')
        return redirect(url_for('gestion_clientes'))
    return render_template('clientes_form.html')

@app.route('/dashboard/clientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    cliente = conn.execute('SELECT * FROM clientes WHERE id_cliente = ? AND id_usuario = ?', (id, user_id)).fetchone()

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']

        conn.execute('UPDATE clientes SET nombre = ?, email = ?, telefono = ?, direccion = ? WHERE id_cliente = ? AND id_usuario = ?',
                     (nombre, email, telefono, direccion, id, user_id))
        conn.commit()
        conn.close()
        flash('Cliente actualizado exitosamente', 'success')
        return redirect(url_for('gestion_clientes'))

    conn.close()
    return render_template('clientes_form.html', cliente=cliente)

# La ruta para eliminar cliente
@app.route('/clientes/eliminar/<int:id>', methods=['POST'])
def eliminar_cliente(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    conn.execute("DELETE FROM clientes WHERE id_cliente = ? AND id_usuario = ?", (id, user_id))
    conn.commit()
    conn.close()
    flash("Cliente eliminado correctamente", "danger")
    # Redirige a 'gestion_clientes'
    return redirect(url_for('gestion_clientes'))

#---------------------------------------------------------------------------------------------------------------------- 
#--------------------------------------------------Ventas--------------------------------------------------------------------

@app.route('/dashboard/ventas', methods=['GET', 'POST'])
def ventas():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()

    if request.method == 'POST':
        id_cliente = request.form.get('id_cliente')
        productos = request.form.getlist('producto[]')
        cantidades = request.form.getlist('cantidad[]')
        metodo_pago = request.form.get('metodo_pago')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if id_cliente == "" or id_cliente is None:
                cursor.execute("INSERT INTO facturas (id_cliente, fecha, total, id_usuario) VALUES (NULL, ?, ?, ?)", (fecha, 0, user_id))
            else:
                cursor.execute("INSERT INTO facturas (id_cliente, fecha, total, id_usuario) VALUES (?, ?, ?, ?)", (id_cliente, fecha, 0, user_id))
            id_factura = cursor.lastrowid
            total_factura = 0

            for i in range(len(productos)):
                id_producto = int(productos[i])
                cantidad = int(cantidades[i])

                producto = cursor.execute("SELECT precio, stock FROM productos WHERE id_producto = ? AND id_usuario = ?", (id_producto, user_id)).fetchone()

                if not producto:
                    conn.rollback()
                    flash("Producto no encontrado.", "danger")
                    return redirect(url_for('ventas'))

                if producto['stock'] < cantidad:
                    conn.rollback()
                    flash(f"Stock insuficiente para el producto ID {id_producto}.", "danger")
                    return redirect(url_for('ventas'))

                precio_unitario = producto['precio']
                subtotal = precio_unitario * cantidad
                total_factura += subtotal
                cursor.execute("""INSERT INTO detalle_factura 
                                  (id_factura, id_producto, cantidad, precio_unitario, subtotal, metodo_pago, id_usuario)
                                  VALUES (?, ?, ?, ?, ?, ?, ?)""",
                               (id_factura, id_producto, cantidad, precio_unitario, subtotal, metodo_pago, user_id))
                cursor.execute("UPDATE productos SET stock = stock - ? WHERE id_producto = ? AND id_usuario = ?", (cantidad, id_producto, user_id))

            cursor.execute("UPDATE facturas SET total = ? WHERE id_factura = ? AND id_usuario = ?", (total_factura, id_factura, user_id))
            conn.commit()
            flash("Venta registrada correctamente.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error al registrar la venta: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for('listado_facturas'))

    conn = get_db_connection()
    clientes = conn.execute("SELECT * FROM clientes WHERE id_usuario = ? ORDER BY nombre", (user_id,)).fetchall()
    productos = conn.execute("SELECT * FROM productos WHERE id_usuario = ? AND stock > 0 ORDER BY descripcion", (user_id,)).fetchall()
    conn.close()
    return render_template('ventas.html', clientes=clientes, productos=productos)


@app.route('/dashboard/listado_facturas', methods=['GET'])
def listado_facturas():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    facturas = conn.execute("""
        SELECT f.id_factura,
               f.fecha,
               f.total,
               (SELECT metodo_pago FROM detalle_factura WHERE id_factura = f.id_factura AND id_usuario = ? LIMIT 1) as metodo_pago,
               c.nombre as cliente,
               IFNULL(SUM(d.cantidad * (d.precio_unitario - p.precio_costo)), 0) as ganancia
        FROM facturas f
        LEFT JOIN clientes c ON f.id_cliente = c.id_cliente AND c.id_usuario = ?
        LEFT JOIN detalle_factura d ON d.id_factura = f.id_factura AND d.id_usuario = ?
        LEFT JOIN productos p ON d.id_producto = p.id_producto AND p.id_usuario = ?
        WHERE f.id_usuario = ?
        GROUP BY f.id_factura
        ORDER BY f.fecha DESC
    """, (user_id, user_id, user_id, user_id, user_id)).fetchall()
    conn.close()
    return render_template('listado_facturas.html', facturas=facturas)


@app.route('/dashboard/factura/<int:id>')
def detalle_factura(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    factura = conn.execute("""SELECT f.id_factura, f.fecha, f.total, c.nombre
                              FROM facturas f
                              LEFT JOIN clientes c ON f.id_cliente = c.id_cliente AND c.id_usuario = ?
                              WHERE f.id_factura = ? AND f.id_usuario = ?""", (user_id, id, user_id)).fetchone()
    detalles = conn.execute("""SELECT d.cantidad, d.precio_unitario, d.subtotal, p.descripcion, d.metodo_pago
                               FROM detalle_factura d
                               JOIN productos p ON d.id_producto = p.id_producto AND p.id_usuario = ?
                               WHERE d.id_factura = ? AND d.id_usuario = ?""", (user_id, id, user_id)).fetchall()
    conn.close()
    return render_template('detalle_factura.html', factura=factura, detalles=detalles)


@app.route('/dashboard/factura/<int:id>/print')
def print_factura(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    tipo = request.args.get('type', 'invoice')
    try:
        copies = int(request.args.get('copies', 1))
    except:
        copies = 1

    conn = get_db_connection()
    factura = conn.execute("""SELECT f.id_factura, f.fecha, f.total, c.nombre
                              FROM facturas f
                              LEFT JOIN clientes c ON f.id_cliente = c.id_cliente AND c.id_usuario = ?
                              WHERE f.id_factura = ? AND f.id_usuario = ?""", (user_id, id, user_id)).fetchone()
    detalles = conn.execute("""SELECT d.cantidad, d.precio_unitario, d.subtotal, p.descripcion, d.metodo_pago
                               FROM detalle_factura d
                               JOIN productos p ON d.id_producto = p.id_producto AND p.id_usuario = ?
                               WHERE d.id_factura = ? AND d.id_usuario = ?""", (user_id, id, user_id)).fetchall()
    conn.close()

    if not factura:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('listado_facturas'))

    return render_template('print_factura.html', factura=factura, detalles=detalles, tipo=tipo, copies=copies)


#------------------------------------------Productos---------------------------------------------------------------------------- 


@app.route('/dashboard/gestion_productos', methods=['GET'])
def gestion_productos():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    productos = conn.execute('SELECT * FROM productos WHERE id_usuario = ? ORDER BY descripcion', (user_id,)).fetchall()
    conn.close()
    return render_template('gestion_productos.html', productos=productos)


@app.route('/dashboard/cajas', methods=['GET'])
def gestion_cajas():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    cajas = conn.execute('SELECT * FROM cajas WHERE id_usuario = ? ORDER BY fecha_apertura DESC', (user_id,)).fetchall()
    conn.close()
    return render_template('gestion_cajas.html', cajas=cajas)


@app.route('/dashboard/cajas/abrir', methods=['POST'])
def abrir_caja():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    usuario = session.get('user')
    monto_apertura = request.form.get('monto_apertura')
    try:
        monto_apertura = float(monto_apertura) if monto_apertura else 0.0
    except:
        monto_apertura = 0.0

    fecha_apertura = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO cajas (fecha_apertura, usuario, monto_apertura, estado, id_usuario) VALUES (?, ?, ?, ?, ?)',
                     (fecha_apertura, usuario, monto_apertura, 'abierta', user_id))
        conn.commit()
        flash('Caja abierta exitosamente', 'success')
    except Exception as e:
        flash(f'Error al abrir caja: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('gestion_cajas'))


@app.route('/dashboard/cajas/cerrar/<int:id>', methods=['POST'])
def cerrar_caja(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    monto_cierre = request.form.get('monto_cierre')
    try:
        monto_cierre = float(monto_cierre) if monto_cierre else None
    except:
        monto_cierre = None

    fecha_cierre = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    try:
        conn.execute('UPDATE cajas SET monto_cierre = ?, fecha_cierre = ?, estado = ? WHERE id_caja = ? AND id_usuario = ?',
                     (monto_cierre, fecha_cierre, 'cerrada', id, user_id))
        conn.commit()
        flash('Caja cerrada correctamente', 'success')
    except Exception as e:
        flash(f'Error al cerrar caja: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('gestion_cajas'))

@app.route('/productos/agregar', methods=['POST'])
def agregar_producto():
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    descripcion = request.form['descripcion']
    stock = int(request.form['stock'])
    codigo_barras = request.form.get('codigo_barras')
    if codigo_barras:
        codigo_barras = codigo_barras.strip()
        if codigo_barras == '':
            codigo_barras = None

    precio = request.form.get('precio')
    precio_costo = request.form.get('precio_costo')
    margen_ganancia = request.form.get('margen_ganancia')

    precio = float(precio) if precio else None
    precio_costo = float(precio_costo) if precio_costo else None
    margen_ganancia = float(margen_ganancia) if margen_ganancia else None

    if precio_costo is not None and margen_ganancia is not None:
        precio = round(precio_costo * (1 + (margen_ganancia / 100)), 2)

    conn = get_db_connection()
    try:
        if codigo_barras:
            exists = conn.execute('SELECT id_producto FROM productos WHERE id_usuario = ? AND codigo_barras = ?', (user_id, codigo_barras)).fetchone()
            if exists:
                flash('El código de barras ya está registrado en otro producto.', 'danger')
                conn.close()
                return redirect(url_for('gestion_productos'))
        conn.execute(
            'INSERT INTO productos (descripcion, precio, stock, precio_costo, margen_ganancia, codigo_barras, id_usuario) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (descripcion, precio, stock, precio_costo, margen_ganancia, codigo_barras, user_id)
        )
        conn.commit()
        flash('Producto agregado exitosamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al agregar producto: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('gestion_productos'))

@app.route('/productos/editar/<int:id>', methods=['POST'])
def editar_producto(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    descripcion = request.form['descripcion']
    stock = int(request.form['stock'])
    codigo_barras = request.form.get('codigo_barras')
    if codigo_barras:
        codigo_barras = codigo_barras.strip()
        if codigo_barras == '':
            codigo_barras = None

    precio = request.form.get('precio')
    precio_costo = request.form.get('precio_costo')
    margen_ganancia = request.form.get('margen_ganancia')

    precio = float(precio) if precio else None
    precio_costo = float(precio_costo) if precio_costo else None
    margen_ganancia = float(margen_ganancia) if margen_ganancia else None

    if precio_costo is not None and margen_ganancia is not None:
        precio = round(precio_costo * (1 + (margen_ganancia / 100)), 2)

    conn = get_db_connection()
    try:
        if codigo_barras:
            exists = conn.execute('SELECT id_producto FROM productos WHERE id_usuario = ? AND codigo_barras = ? AND id_producto != ?', (user_id, codigo_barras, id)).fetchone()
            if exists:
                flash('El código de barras ya está registrado en otro producto.', 'danger')
                conn.close()
                return redirect(url_for('gestion_productos'))
        conn.execute('UPDATE productos SET descripcion = ?, precio = ?, stock = ?, precio_costo = ?, margen_ganancia = ?, codigo_barras = ? WHERE id_producto = ? AND id_usuario = ?',
                     (descripcion, precio, stock, precio_costo, margen_ganancia, codigo_barras, id, user_id))
        conn.commit()
        flash('Producto actualizado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar producto: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('gestion_productos'))


@app.route('/productos/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    if "user" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
        return redirect(url_for("login"))

    user_id = get_current_user_id()
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM productos WHERE id_producto = ? AND id_usuario = ?", (id, user_id))
        conn.commit()
        flash("Producto eliminado correctamente", "success")
    except Exception as e:
        flash(f'Error al eliminar producto: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('gestion_productos'))

#----------------------------------------------------- Configuracion ------------------------------------------------------
@app.route("/dashboard/configuracion", methods=["GET"])
def ver_configuracion():
    return render_template("configuracion.html")
#---------------------------------------------------------------------------------------------------------------------- 





@app.route("/about")
def about():
    return render_template("about.html")



if __name__ == "__main__":
    app.run(debug=True)