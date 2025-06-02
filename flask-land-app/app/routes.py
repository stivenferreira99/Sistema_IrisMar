from flask import Blueprint, render_template, request, flash, redirect, url_for
from sqlalchemy.sql import text
from . import db
from flask import current_app


main = Blueprint('main', __name__)

@main.route('/')
def index():
    return filtrar_propiedades()
@main.route('/filtrar_propiedades', methods=['GET'])
def filtrar_propiedades():
    # Parámetros de filtro existentes
    filtro_tipo = request.args.get('filtro', '')
    departamento_id_str = request.args.get('departamento_id', '') # Corregido
    ciudad_id_str = request.args.get('ciudad_id', '')           # Corregido
    tipo_operacion = request.args.get('tipo_operacion', 'indistinto')
    tipo_propiedad_filter = request.args.get('tipo_propiedad', 'indistinto')

    # Nuevos parámetros para el filtro de precio
    precio_min_str = request.args.get('precio_min', '')
    precio_max_str = request.args.get('precio_max', '')
    moneda_filtro_id_str = request.args.get('moneda_filtro_id', '') # Será "" para "Gs. (por defecto)"

    # Convertir a tipos adecuados y preparar para la plantilla
    precio_min_val = None
    if precio_min_str:
        try:
            precio_min_val = float(precio_min_str)
        except ValueError:
            flash('Valor de precio mínimo inválido.', 'warning')

    precio_max_val = None
    if precio_max_str:
        try:
            precio_max_val = float(precio_max_str)
        except ValueError:
            flash('Valor de precio máximo inválido.', 'warning')

    # moneda_filtro_id_selected contendrá el ID de la moneda como string si se seleccionó una,
    # o una cadena vacía "" si se seleccionó "Gs. (por defecto)".
    moneda_filtro_id_selected = moneda_filtro_id_str
    

    # Cargar datos para los selectores de filtro
    departamentos = db.session.execute(text("SELECT id, nombre FROM departamento")).mappings().fetchall()
    
    # Cargar ciudades, filtradas por departamento si uno está seleccionado
    # y obtener el nombre del departamento para cada ciudad.
    ciudades_query_base = """
        SELECT c.id, c.nombre, d.nombre AS departamento_nombre
        FROM ciudad c
        JOIN departamento d ON c.departamento_id = d.id
    """
    ciudades_params = {}
    ciudades_where_clauses = []

    if departamento_id_str.isdigit():
        ciudades_where_clauses.append("c.departamento_id = :dept_id")
        ciudades_params['dept_id'] = int(departamento_id_str)
    
    final_ciudades_query = ciudades_query_base
    if ciudades_where_clauses:
        final_ciudades_query += " WHERE " + " AND ".join(ciudades_where_clauses)
    final_ciudades_query += " ORDER BY c.nombre"
    ciudades = db.session.execute(text(final_ciudades_query), ciudades_params).mappings().fetchall()
    
    # Cargar monedas para el selector de moneda del filtro
    monedas_cotizacion = db.session.execute(text("SELECT id, tipo_moneda, valor_cotizacion FROM cotizacion ORDER BY tipo_moneda")).mappings().fetchall()

    # Construcción de la consulta SQL dinámica
    query_base = """
        SELECT p.id, p.titulo, p.descripcion, p.tipo_propiedad, p.imagen_cabecera,
               c.nombre AS ciudad_nombre, d.nombre AS departamento_nombre,
               p.precio AS precio_original, p.moneda_id, cot.tipo_moneda AS moneda_original_tipo, cot.valor_cotizacion
        FROM Propiedad p
        JOIN ciudad c ON p.ciudad_id = c.id
        JOIN departamento d ON c.departamento_id = d.id
        LEFT JOIN cotizacion cot ON p.moneda_id = cot.id
    """
    where_clauses = []
    params = {}
    
    from_join_clauses = "" # Para joins adicionales si son necesarios por el filtro de precio

    if departamento_id_str.isdigit():
        where_clauses.append("d.id = :departamento_id")
        params['departamento_id'] = int(departamento_id_str)

    if ciudad_id_str.isdigit():
        where_clauses.append("c.id = :ciudad_id")
        params['ciudad_id'] = int(ciudad_id_str)

    if tipo_operacion != 'indistinto':
        where_clauses.append("p.tipo_operacion = :tipo_operacion")
        params['tipo_operacion'] = tipo_operacion

    if tipo_propiedad_filter != 'indistinto':
        where_clauses.append("p.tipo_propiedad = :tipo_propiedad_filter")
        params['tipo_propiedad_filter'] = tipo_propiedad_filter

    # Lógica del filtro de precios
    precio_min_gs = None
    precio_max_gs = None

    # Si se seleccionó una moneda específica para el filtro (no es "Gs. por defecto")
    if moneda_filtro_id_selected != "" and (precio_min_val is not None or precio_max_val is not None):
        cotizacion_filtro_usuario_obj = next((m for m in monedas_cotizacion if str(m.id) == moneda_filtro_id_selected), None)
        if cotizacion_filtro_usuario_obj:
            valor_cot_usuario = cotizacion_filtro_usuario_obj.valor_cotizacion
            if precio_min_val is not None:
                precio_min_gs = precio_min_val * valor_cot_usuario
            if precio_max_val is not None:
                precio_max_gs = precio_max_val * valor_cot_usuario
    # Si no se seleccionó moneda para el filtro (es "Gs. por defecto") y se ingresaron precios
    elif moneda_filtro_id_selected == "" and (precio_min_val is not None or precio_max_val is not None):
        if precio_min_val is not None:
            precio_min_gs = precio_min_val
        if precio_max_val is not None:
            precio_max_gs = precio_max_val


    if precio_min_gs is not None or precio_max_gs is not None:
        # Aseguramos que la cotización de la propiedad (cot) ya está en el JOIN principal.
        # El precio de la propiedad en Gs es (p.precio * cot.valor_cotizacion)
        # Es importante manejar el caso donde cot.valor_cotizacion podría ser NULL si p.moneda_id no está en cotizacion
        # o si p.moneda_id es NULL. Usaremos COALESCE para tratar NULLs como 1 (asumiendo Gs si no hay cotización)
        # o podrías decidir filtrar esas propiedades. Por simplicidad, asumamos que p.moneda_id siempre es válido
        # y cot.valor_cotizacion existe. Si no, el LEFT JOIN a cotizacion es crucial.

        if precio_min_gs is not None:
            where_clauses.append("(p.precio * COALESCE(cot.valor_cotizacion, 1)) >= :precio_min_gs")
            params['precio_min_gs'] = precio_min_gs
        if precio_max_gs is not None:
            where_clauses.append("(p.precio * COALESCE(cot.valor_cotizacion, 1)) <= :precio_max_gs")
            params['precio_max_gs'] = precio_max_gs


    final_query = query_base
    if from_join_clauses:
        final_query += from_join_clauses # No se usa en esta versión, el JOIN a cotizacion ya está.

    if where_clauses:
        final_query += " WHERE " + " AND ".join(where_clauses)
    
    final_query += " ORDER BY p.id DESC" # O el orden que prefieras

    propiedades = db.session.execute(text(final_query), params).mappings().fetchall()

    return render_template('index.html',
                           propiedades=propiedades,
                           departamentos=departamentos,
                           ciudades=ciudades,
                           filtro=filtro_tipo,
                           departamento_id=departamento_id_str,
                           ciudad_id=ciudad_id_str,
                           tipo_operacion=tipo_operacion,
                           tipo_propiedad=tipo_propiedad_filter,
                           monedas_cotizacion=monedas_cotizacion, # Pasar monedas para el dropdown
                           precio_min_val=precio_min_val,         # Pasar valor para el input
                           precio_max_val=precio_max_val,         # Pasar valor para el input
                           moneda_filtro_id_selected=moneda_filtro_id_selected # Pasar ID seleccionado
                           )


@main.route('/iniciar_sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        contrasena = request.form.get('contrasena')
        try:
            usuario = db.session.execute(
                text('SELECT * FROM Usuario WHERE nombre_usuario = :nombre_usuario AND contrasena = :contrasena'),
                {'nombre_usuario': nombre_usuario, 'contrasena': contrasena}
            ).fetchone()
            if usuario:
                flash('Inicio de sesión exitoso!', 'success')
            else:
                flash('Usuario o contraseña inválidos.', 'danger')
        except Exception as e:
            print(f"Error durante el inicio de sesión: {e}")
            flash('Ocurrió un error. Por favor, inténtalo de nuevo.', 'danger')
    return render_template('login.html')

from flask import flash


@main.route('/registrarse', methods=['GET', 'POST'])
def registrarse():
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        correo_electronico = request.form.get('correo_electronico')
        celular = request.form.get('celular')
        contrasena = request.form.get('contrasena')
        confirmar_contrasena = request.form.get('confirmar_contrasena')

        # Validar que las contraseñas coincidan
        if contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')

        # Validar que el nombre de usuario no exista
        usuario_existente = db.session.execute(
            text('SELECT * FROM Usuario WHERE nombre_usuario = :nombre_usuario'),
            {'nombre_usuario': nombre_usuario}
        ).fetchone()

        if usuario_existente:
            flash('Este usuario ya se encuentra registrado.', 'danger')
            return render_template('register.html')

        try:
            rol = "Comercial"
            db.session.execute(
                text('INSERT INTO Usuario (nombre_usuario, correo_electronico, celular, contrasena, rol) VALUES (:nombre_usuario, :correo_electronico, :celular, :contrasena, :rol)'),
                {'nombre_usuario': nombre_usuario, 'correo_electronico': correo_electronico, 'celular': celular, 'contrasena': contrasena, 'rol': rol}
            )
            db.session.commit()
            flash('Registro exitoso! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('main.iniciar_sesion'))
        except Exception as e:
            print(f"Error durante el registro: {e}")
            flash('El registro falló. Por favor, inténtalo de nuevo.', 'danger')

    return render_template('register.html')

@main.route('/contacto', methods=['GET'])
def contacto():
    return render_template('contact.html')





import os
from flask import request, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Configuración para subir imágenes
UPLOAD_FOLDER = 'static/Img-prop'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import render_template, redirect, url_for, flash
from sqlalchemy.sql import text
from app import db




@main.route('/detalle_propiedad/<int:id>', methods=['GET'])
def detalle_propiedad(id):
    # Recuperar la propiedad principal
    propiedad = db.session.execute(
        text('''
            SELECT 
                p.id, 
                p.titulo, 
                p.descripcion, 
                p.tipo_propiedad,
                c.nombre AS ciudad,
                p.moneda_id  # Asegúrate de que tu tabla Propiedad tenga esta columna
            FROM Propiedad p INNER JOIN ciudad c ON p.ciudad_id = c.id
            WHERE p.id = :id
        '''),
        {'id': id}
    ).fetchone()

    if not propiedad:
        flash('La propiedad no existe o no está disponible.', 'error')
        return redirect(url_for('main.index'))

    # Determinar la categoría y cargar los datos específicos
    if propiedad.tipo_propiedad == 'terreno':
        datos = db.session.execute(
            text('''
                SELECT * 
                FROM datos_terrenos 
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchone()

        # Recuperar el tipo de moneda usando el moneda_id de la tabla Propiedad
        tipo_moneda = None
        if propiedad and propiedad.moneda_id is not None: # Verificar que moneda_id exista y no sea None
            cotizacion = db.session.execute(
                text('SELECT tipo_moneda FROM cotizacion WHERE id = :moneda_id'),
                {'moneda_id': propiedad.moneda_id}
            ).fetchone()
            if cotizacion:
                tipo_moneda = cotizacion.tipo_moneda
        
        # También necesitas cargar las imágenes para la plantilla
        imagenes = db.session.execute(
            text('''
                SELECT dir_img
                FROM img_propiedad  # Asegúrate que esta tabla y consulta sean correctas
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchall()
        return render_template('detalle_terreno.html', propiedad=propiedad, datos=datos, imagenes=imagenes, tipo_moneda=tipo_moneda)

    elif propiedad.tipo_propiedad == 'casa':
        datos = db.session.execute(
            text('''
                SELECT * 
                FROM datos_casas 
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchone()

        

        # Recuperar el tipo de moneda usando el moneda_id de la tabla Propiedad
        tipo_moneda = None
        if propiedad and propiedad.moneda_id is not None: # Verificar que moneda_id exista y no sea None
            cotizacion = db.session.execute(
                text('SELECT tipo_moneda FROM cotizacion WHERE id = :moneda_id'),
                {'moneda_id': propiedad.moneda_id}
            ).fetchone()
            if cotizacion:
                tipo_moneda = cotizacion.tipo_moneda
        
        # También necesitas cargar las imágenes para la plantilla
        imagenes = db.session.execute(
            text('''
                SELECT dir_img
                FROM img_propiedad  # Asegúrate que esta tabla y consulta sean correctas
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchall()

        return render_template('detalle_casa.html', propiedad=propiedad, datos=datos, imagenes=imagenes, tipo_moneda=tipo_moneda)

    elif propiedad.tipo_propiedad == 'departamento':
        datos = db.session.execute(
            text('''
                SELECT * 
                FROM datos_departamentos 
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchone()

        # Recuperar el tipo de moneda usando el moneda_id de la tabla Propiedad
        tipo_moneda = None
        if propiedad and propiedad.moneda_id is not None: # Verificar que moneda_id exista y no sea None
            cotizacion = db.session.execute(
                text('SELECT tipo_moneda FROM cotizacion WHERE id = :moneda_id'),
                {'moneda_id': propiedad.moneda_id}
            ).fetchone()
            if cotizacion:
                tipo_moneda = cotizacion.tipo_moneda
        
        # También necesitas cargar las imágenes para la plantilla
        imagenes = db.session.execute(
            text('''
                SELECT dir_img
                FROM img_propiedad  # Asegúrate que esta tabla y consulta sean correctas
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchall()
        return render_template('detalle_departamento.html', propiedad=propiedad, datos=datos, imagenes=imagenes, tipo_moneda=tipo_moneda)

    elif propiedad.tipo_propiedad == 'quinta':
        datos = db.session.execute(
            text('''
                SELECT * 
                FROM datos_quintas 
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchone()

        # Recuperar el tipo de moneda usando el moneda_id de la tabla Propiedad
        tipo_moneda = None
        if propiedad and propiedad.moneda_id is not None: # Verificar que moneda_id exista y no sea None
            cotizacion = db.session.execute(
                text('SELECT tipo_moneda FROM cotizacion WHERE id = :moneda_id'),
                {'moneda_id': propiedad.moneda_id}
            ).fetchone()
            if cotizacion:
                tipo_moneda = cotizacion.tipo_moneda
        
        # También necesitas cargar las imágenes para la plantilla
        imagenes = db.session.execute(
            text('''
                SELECT dir_img
                FROM img_propiedad  # Asegúrate que esta tabla y consulta sean correctas
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchall()
        return render_template('detalle_quinta.html', propiedad=propiedad, datos=datos, imagenes=imagenes, tipo_moneda=tipo_moneda)

    elif propiedad.tipo_propiedad == 'deposito':
        datos = db.session.execute(
            text('''
                SELECT * 
                FROM datos_depositos 
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchone()

        # Recuperar el tipo de moneda usando el moneda_id de la tabla Propiedad
        tipo_moneda = None
        if propiedad and propiedad.moneda_id is not None: # Verificar que moneda_id exista y no sea None
            cotizacion = db.session.execute(
                text('SELECT tipo_moneda FROM cotizacion WHERE id = :moneda_id'),
                {'moneda_id': propiedad.moneda_id}
            ).fetchone()
            if cotizacion:
                tipo_moneda = cotizacion.tipo_moneda
        
        # También necesitas cargar las imágenes para la plantilla
        imagenes = db.session.execute(
            text('''
                SELECT dir_img
                FROM img_propiedad  # Asegúrate que esta tabla y consulta sean correctas
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchall()
        return render_template('detalle_deposito.html', propiedad=propiedad, datos=datos, imagenes=imagenes, tipo_moneda=tipo_moneda)

    elif propiedad.tipo_propiedad == 'oficina':
        datos = db.session.execute(
            text('''
                SELECT * 
                FROM datos_oficinas 
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchone()

        # Recuperar el tipo de moneda usando el moneda_id de la tabla Propiedad
        tipo_moneda = None
        if propiedad and propiedad.moneda_id is not None: # Verificar que moneda_id exista y no sea None
            cotizacion = db.session.execute(
                text('SELECT tipo_moneda FROM cotizacion WHERE id = :moneda_id'),
                {'moneda_id': propiedad.moneda_id}
            ).fetchone()
            if cotizacion:
                tipo_moneda = cotizacion.tipo_moneda
        
        # También necesitas cargar las imágenes para la plantilla
        imagenes = db.session.execute(
            text('''
                SELECT dir_img
                FROM img_propiedad  # Asegúrate que esta tabla y consulta sean correctas
                WHERE id_propiedad = :id
            '''),
            {'id': id}
        ).fetchall()
        return render_template('detalle_oficina.html', propiedad=propiedad, datos=datos, imagenes=imagenes, tipo_moneda=tipo_moneda)
    else:
        flash('Categoría de propiedad no reconocida.', 'error')
        return redirect(url_for('main.index'))
    



    
@main.route('/ver_datos_propiedad/<int:id_propiedad>', methods=['GET'])
def ver_datos_propiedad(id_propiedad):
    # Consulta para obtener los datos de la propiedad desde datos_propiedad y item_gral
    datos_propiedad = db.session.execute(
        text('''
            SELECT 
                a.item AS id,
                b.nombre AS nombre,
                a.valor AS valor
            FROM datos_propiedad AS a
            INNER JOIN item_gral AS b ON b.Item_id = a.item
            WHERE a.id_propiedad = :id_propiedad AND a.valor IS NOT NULL
        '''),
        {'id_propiedad': id_propiedad}
    ).fetchall()

    # Manejar la excepción si no se encuentran datos
    if not datos_propiedad:
        flash('No se encontraron datos para esta propiedad.', 'error')
        return redirect(url_for('main.index'))

    return render_template('ver_datos_propiedad.html', datos_propiedad=datos_propiedad)