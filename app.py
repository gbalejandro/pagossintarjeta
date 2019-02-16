from flask import Flask, request, render_template, json, jsonify
from logicanegocios import PagoSinTarjeta
from flask_cors import CORS
from xml.etree import ElementTree as ET

app = Flask(__name__)
CORS(app)

@app.route('/')
def output():
	return render_template('pagos.html')

@app.route('/api/index', methods = ['GET'])
def index():
    return "Hello, World2!"

@app.route('/postmethod', methods = ['POST'])
def post_javascript_data():
    global encrip
    if request.method == 'POST':
        name = request.form['nombre']
        number = str(request.form['numero'])
        month = str(request.form['mes'])
        year = str(request.form['anio'])
        cvv = str(request.form['cvv'])

    req = PagoSinTarjeta('Z703SOUS0','8ROOEJVYS4')
    req.nombre = name
    req.numerotarj = number
    req.expmonth = month
    req.expyear = year
    req.cvv = cvv
    texto = req.createxto()
    encrypted = req.encrypt(texto)
    encrip = req.crearequest(encrypted)
    return jsonify(result=encrip)

@app.route('/api/redirige', methods = ['GET'])
def redirige():
    global encrip
    return render_template('redirige.html', xml=encrip)

@app.route('/api/response', methods = ['POST'])
def obtiene_venta():
    if not request.form.get('strIdCompany'):
        respuesta = request.form.get('strResponse')
    else:
        respuesta = request.form.get('strResponse')
        company = request.form.get('strIdCompany')
        merchant = request.form.get('strIdMerchant')
    #print(respuesta)
    logican = PagoSinTarjeta('', '')
    response1 = logican.decrypt(respuesta)
    response1 = response1.decode('utf-8')
    #print(response1)
    response1 = response1.replace("<?xml version='1.0'encoding='UTF-8'?>", '')
    if not request.form.get('strIdCompany'):
        values = ET.fromstring(response1).findall('.//CENTEROFPAYMENTS')
        for val in values:
            resp = val.find('response').text
            numaut = val.find('auth').text
            referencia = val.find('reference').text
            voucher_cliente = val.find('voucher_cliente').text
            voucher_comercio = val.find('voucher_comercio').text
            vouchcl = logican.decrypt(voucher_cliente)
            print(vouchcl)
            vouchco = logican.decrypt(voucher_comercio)
            print(vouchco)

            if (resp == 'approved'):
                respuesta2 = 'Su transacción ha sido aprobada satisfactoriamente con el número de autorización ' + numaut
                return render_template('respuesta.html', respuesta=respuesta2)
    else:
        values = ET.fromstring(response1).findall('.//CENTEROFPAYMENTS')
        for val in values:
            resp = val.find('response').text
            error = val.find('nb_error').text

            if (resp == 'denied'):
                return render_template('respuesta.html', respuesta=resp)
            elif (resp == 'error'):
                return render_template('respuesta.html', respuesta=error)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)