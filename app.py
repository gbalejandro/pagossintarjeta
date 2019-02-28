from flask import Flask, request, render_template, json, jsonify
from logicanegocios import PagoSinTarjeta
from flask_cors import CORS
from xml.etree import ElementTree as ET

app = Flask(__name__)
CORS(app)
req = PagoSinTarjeta()

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

    req.nombre = name
    req.numerotarj = number
    req.expmonth = month
    req.expyear = year
    req.cvv = cvv
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
    #print(respuesta)
    #logican = PagoSinTarjeta('', '')
    response1 = req.decrypt(respuesta)
    response1 = response1.decode('utf-8')
    print(response1)
    response1 = response1.replace("<?xml version='1.0'encoding='UTF-8'?>", '')
    values = ET.fromstring(response1).findall('.//CENTEROFPAYMENTS')
    for val in values:
        resp = val.find('response').text

        if (resp == 'approved'):
            numaut = val.find('auth').text
            respuesta2 = 'Su transacción ha sido aprobada satisfactoriamente con el número de autorización ' + numaut
            referencia = val.find('reference').text
            voucher_cliente = val.find('voucher_cliente').text
            voucher_comercio = val.find('voucher_comercio').text
            vouchcl = req.decrypt_voucher(voucher_cliente)
            print(vouchcl)
            vouchco = req.decrypt_voucher(voucher_comercio)
            print(vouchco)
            return render_template('respuesta.html', respuesta=respuesta2)           
        elif (resp == 'denied'):
            return render_template('respuesta.html', respuesta=resp)
        else: # es un error
            error = val.find('nb_error').text
            return render_template('respuesta.html', respuesta=error)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)