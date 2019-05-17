import datetime

from app import db

class Configuration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_banco = db.Column(db.String(80), nullable=False)
    password_banco = db.Column(db.String(80), nullable=False)
    sucursal = db.Column(db.String(50))
    nombre = db.Column(db.String(50))
    terminal = db.Column(db.String(50))
    ambiente = db.Column(db.String(50))

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.datetime.now) #onupdate=datetime.now()
    hora = db.Column(db.String(5))
    referencia = db.Column(db.String(50))
    descripcion = db.Column(db.String(50))
    importe = db.Column(db.Float(10, 2))
    numero_autorizacion = db.Column(db.String(20))
    numero_operacion = db.Column(db.String(20))
    estatus = db.Column(db.String(1))
    terminal = db.Column(db.String(50), nullable=False, unique=True)