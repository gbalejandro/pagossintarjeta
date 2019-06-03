import os
import socket
import time
import datetime
import sqlite3

from flask import Flask, request, render_template, json, jsonify
from flask_bootstrap import Bootstrap
from logicanegocios import PagoSinTarjeta
from flask_cors import CORS
from xml.etree import ElementTree as ET

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "params.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config["SQLALCHEMY_TRACK_MODIFICATION"] = True

db = SQLAlchemy(app)

CORS(app)
req = PagoSinTarjeta()

class Configuration(db.Model):
    __tablename__ = 'Configuration'

    id = db.Column(db.Integer, primary_key=True)
    usuario_banco = db.Column(db.String(80), nullable=False)
    password_banco = db.Column(db.String(80), nullable=False)
    sucursal = db.Column(db.String(50))
    nombre = db.Column(db.String(50))
    terminal = db.Column(db.String(50))
    ambiente = db.Column(db.String(50))

class Transacciones(db.Model):
    __tablename__ = 'Transacciones'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False) #onupdate=datetime.now()
    hora = db.Column(db.String(5))
    referencia = db.Column(db.String(50))
    descripcion = db.Column(db.String(50))
    importe = db.Column(db.Float(10, 2))
    numero_autorizacion = db.Column(db.String(20))
    numero_operacion = db.Column(db.String(20))
    estatus = db.Column(db.String(1))
    terminal = db.Column(db.String(50))

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
    #print(req.nombre)
    req.numerotarj = str(request.form['numero'])
    #print(req.numerotarj)
    req.expmonth = str(request.form['mes'])
    #print(req.expmonth)
    req.expyear = str(request.form['anio'])
    #print(req.expyear)
    req.cvv = str(request.form['cvv'])
 
    req.obtener_credenciales()

    if req.numerotarj[:1] == '3':
        texto = req.createxto_amex()
    else:
        texto = req.createxto()
    #print(texto)
    encrypted = req.encrypt(texto)
    #print(encrypted)
    encrip = req.crearequest(encrypted)
    #print(encrip)
    return jsonify(result=encrip)

@app.route('/api/redirige', methods = ['GET'])
def redirige():
    contexto = 'Va a realizar una transacción por: $ ' + req.importe + ' pesos, a nombre de: ' + req.nombre + ', con el número de tarjeta terminación: XXXX-XXXX-XXXX-' + req.numerotarj[-4:]            
    global encrip
    return render_template('redirige.html', xml=encrip, texto=contexto)

@app.route('/api/response', methods = ['POST'])
def obtiene_venta():
    #print('si llega aquí')
    respuesta = request.form.get('strResponse')
    company = request.form.get('strIdCompany')
    merchant = request.form.get('strIdMerchant')
    #respuesta2 = req.obtener_response(respuesta)
    #return render_template('respuesta.html', respuesta=respuesta2)
    #print('Primer respuesta ' + respuesta)
    response1 = req.decrypt(respuesta)
    response1 = response1.decode('utf-8')
    print('Respuesta decodificada ' + response1)
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
            referencia = val.find('reference').text
            voucher_cliente = val.find('voucher_cliente').text
            voucher_comercio = val.find('voucher_comercio').text
            vouchcl = req.decrypt_voucher(voucher_cliente)
            #print(vouchcl)
            vouchco = req.decrypt_voucher(voucher_comercio)
            #print(vouchco)
            # inserto el registro de la venta satisfactoria
            fecha = date.today()
            #fechadatetime = datetime.datetime.now()
            #fechad = datetime.strptime(fechadatetime, '%d/%m/%Y')
            fechan = datetime.strftime(fecha, '%Y-%m-%d')
            now = datetime.now()
            hora = now.hour 
            minuto = now.minute
            if len(str(hora)) == 1:
                hora = '0' + str(hora)

            if len(str(minuto)) == 1:
                minuto = '0' + str(minuto)

            hora = str(hora) + ':' + str(minuto)
            #print(hora)
            estatus = 'A'
            nombre_equipo = socket.gethostname()
            #print(nombre_equipo)
            objeto_venta = Transacciones(fecha=fecha, hora=hora, referencia=referencia, descripcion=descripcion, importe=importe, numero_autorizacion=numaut, numero_operacion=numop, estatus=estatus, terminal=nombre_equipo)
            db.session.add(objeto_venta)
            db.session.commit()
            respuesta3 = 'APROVADA'
            importe = '$ ' + importe + ' PESOS'
            respuesta4 = 'ÉXITO'
            try:
                contexto = {'respuesta3':respuesta3, 'numaut':numaut, 'numop':numop, 'importe':importe, 'tarjeta':tarjeta, 'numtarj':numtarj, 'respuesta4':respuesta4}
                return render_template('respuesta.html', **contexto) 
            except e:
                return str(e)
        elif (resp == 'denied'):
            respuesta3 = resp
            respuesta4 = 'DENEGADA'
            try:
                return render_template('respuesta.html', respuesta3=respuesta3, respuesta4=respuesta4)
            except e:
                return str(e)
        else: # es un error
            respuesta3 = val.find('nb_error').text
            respuesta4 = 'ERROR'
            try:
                return render_template('respuesta.html', respuesta3=respuesta3, respuesta4=respuesta4)
            except e:
                return str(e)

@app.route('/consulta', methods=['GET', 'POST'])
def buscar_transaccion():
    transacciones = []
    referencia = []
    if request.form:
        #transacciones = Response.query.all()
        fechan = str(request.form['fecha'])
        referencian = str(request.form['referencia'])

        response1 = req.consulta_transacciones(fechan, referencian)
        response1 = response1.replace('<transaccionesCautM></transaccionesCautM>', '')
        values = ET.fromstring(response1).findall('.//transaccion')

        for val in values:
            referencia = val.find('nb_referencia').text
            importe = val.find('nu_importe').text
            fecha1 = val.find('fh_registro').text
            fecha = fecha1[0:10]
            fechad = datetime.strptime(fecha, '%d/%m/%Y')
            fechan = datetime.strftime(fechad, '%Y-%m-%d')
            hora = fecha1[-5:]
            numero_autorizacion = val.find('nu_auth').text
            numero_operacion = val.find('nu_operaion').text
            responset = val.find('nb_response').text

            if responset == 'approved':
                estatus = 'A'
            else:
                estatus = 'D'

            # constrans = []
            # constrans = session.query(Transacciones).filter_by(referencia=referencia,fecha=fechan)
            # for row in constrans:
            #     print(row.referencia)
            # else:
            #     objeto_venta = Transacciones(fecha=fechan, hora=hora, referencia=referencia, descripcion='INTERFACE', importe=importe, numero_autorizacion=numero_autorizacion, numero_operacion=numero_operacion, estatus=estatus, terminal='BANCO')
            #     session.add(objeto_venta)
            #     session.commit()

            db1 = sqlite3.connect('params.db')
            c = db1.cursor()
            
            c.execute("select * from transacciones where referencia = '" + referencia + "' and fecha = '" + fechan + "'")
            row = c.fetchone()
            if row is None:
                c.execute('''INSERT INTO transacciones(fecha, hora, referencia, descripcion, importe, numero_autorizacion, numero_operacion, estatus, terminal) VALUES(?,?,?,?,?,?,?,?,?)''', (fechan, hora, referencia, 'INTERFACE', importe, numero_autorizacion, numero_operacion, estatus, 'BANCO'))
                db1.commit()
            db1.close()
        
        if referencian:
            transacciones = Transacciones.query.filter_by(fecha=fechan,referencia=referencia).first()
            #print(transacciones.referencia)
            transact_dict = [{
                'referencia': transacciones.referencia,
                'fecha': transacciones.fecha,
                'hora': transacciones.hora,
                'importe': transacciones.importe,
                'numero_autorizacion': transacciones.numero_autorizacion,
                'numero_operacion': transacciones.numero_operacion
            }]
            return render_template('consulta.html', transacciones=transact_dict)
        else:
            transacciones = Transacciones.query.filter_by(fecha=fechan).all()
            # print(transacciones[0].importe)
            # print(len(transacciones))
            # for i in (0, len(transacciones)-1):
            #     print(transacciones[i].referencia)
            return render_template('consulta_varios.html', transacciones=transacciones)
    return render_template('consulta.html')

if __name__ == "__main__":
    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', debug=True)