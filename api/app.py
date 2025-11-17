# api/app.py
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from .models import db, User, AnalisisSubasta
from .forms import LoginForm, RegisterForm
from datetime import datetime
import os

# Crear la aplicación Flask
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))

# Configuración
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

# Importar la lógica de subastas
from . import subasta_logic

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Crear las tablas
with app.app_context():
    db.create_all()

# ================== RUTAS PRINCIPALES ==================

@app.route('/')
def index():
    """Página de inicio"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de usuarios"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Verificar si el usuario ya existe
        if User.query.filter_by(email=form.email.data).first():
            flash('El email ya está registrado.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=form.username.data).first():
            flash('El nombre de usuario ya está en uso.', 'danger')
            return redirect(url_for('register'))
        
        # Crear nuevo usuario
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('¡Registro exitoso! Por favor inicia sesión.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'¡Bienvenido {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard del usuario"""
    # Obtener los últimos análisis del usuario
    analisis_recientes = AnalisisSubasta.query.filter_by(user_id=current_user.id)\
        .order_by(AnalisisSubasta.fecha_creacion.desc()).limit(5).all()
    
    return render_template('dashboard.html', analisis=analisis_recientes)

@app.route('/suscribirse')
@login_required
def suscribirse():
    """Activar suscripción (simulado - 30 días)"""
    current_user.activar_suscripcion(dias=30)
    db.session.commit()
    flash('¡Suscripción activada por 30 días!', 'success')
    return redirect(url_for('dashboard'))

# ================== RUTAS DE ANÁLISIS DE SUBASTAS ==================

@app.route('/analisis/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_analisis():
    """Crear un nuevo análisis de subasta"""
    # Verificar suscripción
    if not current_user.tiene_suscripcion_valida():
        flash('Necesitas una suscripción activa para realizar análisis.', 'warning')
        return redirect(url_for('suscribirse'))
    
    if request.method == 'POST':
        # Guardar en sesión para pasar a la siguiente página
        session['analisis_temp'] = request.form.to_dict()
        return redirect(url_for('calcular_analisis'))
    
    return render_template('analisis.html')

@app.route('/analisis/extraer', methods=['POST'])
@login_required
def extraer_datos():
    """Extrae datos automáticamente desde URL del BOE"""
    if not current_user.tiene_suscripcion_valida():
        return jsonify({'error': 'Suscripción requerida'}), 403
    
    url_subasta = request.json.get('url')
    
    if not url_subasta:
        return jsonify({'error': 'URL no proporcionada'}), 400
    
    try:
        datos = subasta_logic.extraer_datos_subasta(url_subasta)
        return jsonify({'success': True, 'datos': datos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analisis/calcular', methods=['GET', 'POST'])
@login_required
def calcular_analisis():
    """Calcula rentabilidad y guarda el análisis"""
    if not current_user.tiene_suscripcion_valida():
        flash('Necesitas una suscripción activa.', 'warning')
        return redirect(url_for('suscribirse'))
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            datos = request.form.to_dict()
            
            # Crear nuevo análisis
            analisis = AnalisisSubasta(user_id=current_user.id)
            
            # Datos de subasta
            analisis.url_subasta = datos.get('url_subasta', '')
            analisis.identificador = datos.get('identificador', '')
            analisis.fecha_conclusion = datos.get('fecha_conclusion', '')
            analisis.cantidad_reclamada = float(datos.get('cantidad_reclamada', 0) or 0)
            analisis.valor_subasta = float(datos.get('valor_subasta', 0) or 0)
            analisis.tasacion = float(datos.get('tasacion', 0) or 0)
            analisis.tramos_pujas = float(datos.get('tramos_pujas', 0) or 0)
            analisis.deposito = float(datos.get('deposito', 0) or 0)
            analisis.direccion = datos.get('direccion', '')
            analisis.referencia_catastral = datos.get('referencia_catastral', '')
            
            # Puja
            analisis.puja = float(datos.get('puja', 0) or 0)
            
            # Calcular porcentaje de puja
            if analisis.puja and analisis.valor_subasta:
                resultado, error = subasta_logic.calcular_porcentaje_puja(
                    analisis.puja, analisis.valor_subasta
                )
                if resultado:
                    analisis.porcentaje_puja = resultado['porcentaje']
                    analisis.veredicto = resultado['veredicto']
            
            # Datos de rentabilidad
            analisis.valor_referencia = float(datos.get('valor_referencia', 0) or 0)
            analisis.itp_porcentaje = float(datos.get('itp_porcentaje', 7) or 7)
            
            # Calcular ITP y notaría
            if analisis.valor_referencia:
                resultado, error = subasta_logic.calcular_itp_notaria(
                    analisis.valor_referencia, analisis.itp_porcentaje
                )
                if resultado:
                    analisis.itp_calculado = resultado['itp']
                    analisis.notaria_registro = resultado['notaria']
            
            # Costes judiciales
            analisis.ano_procedimiento = int(datos.get('ano_procedimiento', 0) or 0)
            analisis.ibi_anual = float(datos.get('ibi_anual', 0) or 0)
            
            # Calcular IBI judicial
            if analisis.ibi_anual and analisis.ano_procedimiento:
                resultado, error = subasta_logic.calcular_ibi_judicial(
                    analisis.ibi_anual, analisis.ano_procedimiento
                )
                if resultado:
                    analisis.anos_total = resultado['anos_total']
                    analisis.ibi_total = resultado['total_ibi']
            
            # Comunidad
            analisis.comunidad_anual = float(datos.get('comunidad_anual', 0) or 0)
            
            if analisis.comunidad_anual and analisis.anos_total:
                resultado, error = subasta_logic.calcular_comunidad_judicial(
                    analisis.comunidad_anual, analisis.anos_total
                )
                if resultado:
                    analisis.comunidad_total = resultado
            
            # Otros costes
            analisis.alarmas = float(datos.get('alarmas', 0) or 0)
            analisis.suministros = float(datos.get('suministros', 0) or 0)
            analisis.reforma = float(datos.get('reforma', 0) or 0)
            
            # Calcular total inversión
            resultado, error = subasta_logic.calcular_total_inversion(
                analisis.puja,
                analisis.itp_calculado,
                analisis.notaria_registro,
                analisis.ibi_total,
                analisis.comunidad_total,
                analisis.alarmas,
                analisis.suministros,
                analisis.reforma
            )
            
            if resultado:
                analisis.total_inversion = resultado
            
            # Escenarios de venta
            analisis.venta_bajo = float(datos.get('venta_bajo', 0) or 0)
            analisis.venta_medio = float(datos.get('venta_medio', 0) or 0)
            analisis.venta_alto = float(datos.get('venta_alto', 0) or 0)
            
            # Calcular márgenes y rentabilidad
            if analisis.total_inversion:
                # Escenario bajo
                if analisis.venta_bajo:
                    resultado, error = subasta_logic.calcular_margen_rentabilidad(
                        analisis.venta_bajo, analisis.total_inversion
                    )
                    if resultado:
                        analisis.margen_bajo = resultado['margen']
                        analisis.rentabilidad_bajo = resultado['rentabilidad']
                
                # Escenario medio
                if analisis.venta_medio:
                    resultado, error = subasta_logic.calcular_margen_rentabilidad(
                        analisis.venta_medio, analisis.total_inversion
                    )
                    if resultado:
                        analisis.margen_medio = resultado['margen']
                        analisis.rentabilidad_medio = resultado['rentabilidad']
                
                # Escenario alto
                if analisis.venta_alto:
                    resultado, error = subasta_logic.calcular_margen_rentabilidad(
                        analisis.venta_alto, analisis.total_inversion
                    )
                    if resultado:
                        analisis.margen_alto = resultado['margen']
                        analisis.rentabilidad_alto = resultado['rentabilidad']
            
            # Notas
            analisis.notas = datos.get('notas', '')
            
            # Guardar en base de datos
            db.session.add(analisis)
            db.session.commit()
            
            flash('¡Análisis guardado exitosamente!', 'success')
            return redirect(url_for('ver_analisis', analisis_id=analisis.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar el análisis: {str(e)}', 'danger')
            return redirect(url_for('nuevo_analisis'))
    
    return render_template('analisis.html')

@app.route('/analisis/<int:analisis_id>')
@login_required
def ver_analisis(analisis_id):
    """Ver un análisis específico"""
    analisis = AnalisisSubasta.query.get_or_404(analisis_id)
    
    # Verificar que el análisis pertenece al usuario actual
    if analisis.user_id != current_user.id:
        flash('No tienes permiso para ver este análisis.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('resultados.html', analisis=analisis)

@app.route('/analisis/lista')
@login_required
def lista_analisis():
    """Lista todos los análisis del usuario"""
    analisis = AnalisisSubasta.query.filter_by(user_id=current_user.id)\
        .order_by(AnalisisSubasta.fecha_creacion.desc()).all()
    
    return render_template('lista_analisis.html', analisis=analisis)

@app.route('/analisis/eliminar/<int:analisis_id>', methods=['POST'])
@login_required
def eliminar_analisis(analisis_id):
    """Eliminar un análisis"""
    analisis = AnalisisSubasta.query.get_or_404(analisis_id)
    
    # Verificar que el análisis pertenece al usuario actual
    if analisis.user_id != current_user.id:
        flash('No tienes permiso para eliminar este análisis.', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(analisis)
    db.session.commit()
    
    flash('Análisis eliminado correctamente.', 'success')
    return redirect(url_for('lista_analisis'))

# Ejecutar la aplicación
# Ejecutar la aplicación (solo para desarrollo local)
if __name__ == '__main__':
    app.run(debug=True)

