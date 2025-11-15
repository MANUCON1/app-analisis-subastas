# api/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Campos de suscripción
    suscripcion_activa = db.Column(db.Boolean, default=False)
    fecha_suscripcion = db.Column(db.DateTime, nullable=True)
    fecha_expiracion = db.Column(db.DateTime, nullable=True)
    
    # Relación con análisis de subastas
    analisis = db.relationship('AnalisisSubasta', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Establece la contraseña hasheada"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def activar_suscripcion(self, dias=30):
        """Activa la suscripción por X días"""
        self.suscripcion_activa = True
        self.fecha_suscripcion = datetime.utcnow()
        self.fecha_expiracion = datetime.utcnow() + timedelta(days=dias)
    
    def tiene_suscripcion_valida(self):
        """Verifica si la suscripción está activa y no ha expirado"""
        if not self.suscripcion_activa:
            return False
        if self.fecha_expiracion and datetime.utcnow() > self.fecha_expiracion:
            self.suscripcion_activa = False
            db.session.commit()
            return False
        return True


class AnalisisSubasta(db.Model):
    __tablename__ = 'analisis_subastas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Datos de la subasta
    url_subasta = db.Column(db.String(500))
    identificador = db.Column(db.String(200))
    fecha_conclusion = db.Column(db.String(100))
    cantidad_reclamada = db.Column(db.Float)
    valor_subasta = db.Column(db.Float)
    tasacion = db.Column(db.Float)
    tramos_pujas = db.Column(db.Float)
    deposito = db.Column(db.Float)
    direccion = db.Column(db.String(500))
    referencia_catastral = db.Column(db.String(100))
    
    # Datos de puja
    puja = db.Column(db.Float)
    porcentaje_puja = db.Column(db.Float)
    veredicto = db.Column(db.String(50))
    
    # Datos de rentabilidad
    valor_referencia = db.Column(db.Float)
    itp_porcentaje = db.Column(db.Float, default=7.0)
    itp_calculado = db.Column(db.Float)
    notaria_registro = db.Column(db.Float)
    
    # Costes judiciales
    ano_procedimiento = db.Column(db.Integer)
    anos_total = db.Column(db.Integer)
    ibi_anual = db.Column(db.Float)
    ibi_total = db.Column(db.Float)
    comunidad_anual = db.Column(db.Float)
    comunidad_total = db.Column(db.Float)
    
    # Otros costes
    alarmas = db.Column(db.Float, default=0)
    suministros = db.Column(db.Float, default=0)
    reforma = db.Column(db.Float, default=0)
    
    # Inversión total
    total_inversion = db.Column(db.Float)
    
    # Escenarios de venta
    venta_bajo = db.Column(db.Float)
    margen_bajo = db.Column(db.Float)
    rentabilidad_bajo = db.Column(db.Float)
    
    venta_medio = db.Column(db.Float)
    margen_medio = db.Column(db.Float)
    rentabilidad_medio = db.Column(db.Float)
    
    venta_alto = db.Column(db.Float)
    margen_alto = db.Column(db.Float)
    rentabilidad_alto = db.Column(db.Float)
    
    # Notas adicionales
    notas = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AnalisisSubasta {self.identificador}>'
