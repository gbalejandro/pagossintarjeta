import os
import socket
import time
import datetime

from flask import Flask, request, render_template, json, jsonify
from logicanegocios import PagoSinTarjeta
from flask_cors import CORS
from xml.etree import ElementTree as ET

from config import Configuration
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Configuration)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///params.db'
db = SQLAlchemy(app)

CORS(app)
req = PagoSinTarjeta()

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
    fecha = db.Column(db.DateTime, nullable = False) #onupdate=datetime.now()
    hora = db.Column(db.String(5))
    referencia = db.Column(db.String(50))
    descripcion = db.Column(db.String(50))
    importe = db.Column(db.Float(10, 2))
    numero_autorizacion = db.Column(db.String(20))
    numero_operacion = db.Column(db.String(20))
    estatus = db.Column(db.String(1))
    terminal = db.Column(db.String(50), nullable=False, unique=True)

@app.route('/')
def output():
	return render_template('pagos.html')

@app.route('/api/index', methods = ['GET'])
def index():
    return "Hello, World2!"

@app.route('/postmethod', methods = ['POST'])
def post_javascript_data():
    global encrip
    req.nombre = request.form['nombre']
    req.numerotarj = str(request.form['numero'])
    req.expmonth = str(request.form['mes'])
    req.expyear = str(request.form['anio'])
    req.cvv = str(request.form['cvv'])
    # primero valido la informacion
    #esvalido = req.validar_informacion()
    # Obtengo las credenciales de acceso al banco
    req.obtener_credenciales() 
    texto = req.createxto()
    print(texto)
    encrypted = req.encrypt(texto)
    #print(encrypted)
    encrip = req.crearequest(encrypted)
    #print(encrip)
    return jsonify(result=encrip)

@app.route('/api/redirige', methods = ['GET'])
def redirige():
    global encrip
    return render_template('redirige.html', xml=encrip)

@app.route('/api/response', methods = ['POST'])
def obtiene_venta():
    #print('si llega aquí')
    respuesta = request.form.get('strResponse')
    company = request.form.get('strIdCompany')
    merchant = request.form.get('strIdMerchant')
    respuesta2 = req.obtener_response(respuesta)
    #return render_template('respuesta.html', respuesta=respuesta2)
    #print('Primer respuesta ' + respuesta)
    response1 = req.decrypt(respuesta)
    response1 = response1.decode('utf-8')
    #print('Respuesta decodificada ' + response1)
    response1 = response1.replace("<?xml version='1.0'encoding='UTF-8'?>", '')
    values = ET.fromstring(response1).findall('.//CENTEROFPAYMENTS')
    for val in values:
        resp = val.find('response').text

        if (resp == 'approved'):
            numaut = val.find('auth').text
            numop = val.find('foliocpagos').text
            importe = val.find('amount').text
            tarjeta = val.find('cc_type').text
            numtarj = val.find('cc_number').text
            descripcion = val.find('friendly_response').text
            respuesta2 = 'Su transacción ha sido aprobada satisfactoriamente con el número de autorización ' + numaut + ' y el número de operación: ' + numop + ', por la cantidad de: $ ' + importe + ' pesos, para la tarjeta: ' + tarjeta + ' con terminación: ' + numtarj
            referencia = val.find('reference').text
            voucher_cliente = val.find('voucher_cliente').text
            voucher_comercio = val.find('voucher_comercio').text
            vouchcl = req.decrypt_voucher(voucher_cliente)
            #print(vouchcl)
            vouchco = req.decrypt_voucher(voucher_comercio)
            #print(vouchco)
            # inserto el registro de la venta satisfactoria
            fecha = datetime.now()
            #print(fecha)
            hora = time.strftime('%H:%M')
            #print(hora)
            estatus = 'A'
            nombre_equipo = socket.gethostname()
            #print(nombre_equipo)
            objeto_venta = Response(fecha=fecha, hora=hora, referencia=referencia, descripcion=descripcion, importe=importe, numero_autorizacion=numaut, numero_operacion=numop, estatus=estatus, terminal=nombre_equipo)
            db.session.add(objeto_venta)
            db.session.commit()
            return render_template('respuesta.html', respuesta=respuesta2)           
        elif (resp == 'denied'):
            return render_template('respuesta.html', respuesta=resp)
        else: # es un error
            error = val.find('nb_error').text
            return render_template('respuesta.html', respuesta=error)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)