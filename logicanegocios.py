import requests
import base64
import codecs
import sqlite3
import hashlib
import re
import threading
import suds

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random

import xml.etree.cElementTree as ET
from xml.etree.ElementTree import tostring
from arc4 import ARC4
from suds.client import Client

MOD = 256

class PagoSinTarjeta(object):
    def __init__(self):
        self.usuario = ''
        self.password = ''
        self.compania = 'Z703'
        self.sucursal = '210'
        self.referencia = 'GOC12373'
        self.importe = '2.00'
        self.key_bytes = 16 #(AES128) # parametro de encriptación, parametro fijo
        self.merchant = '158198' # Siempre va a ser de contado, parámetro fijo
        self.nombre = ''
        self.numerotarj = ''
        self.expmonth = ''
        self.expyear = ''
        self.cvv = '' # cuando son visa y M/C
        self.semilla = 'A2832DE3C0B2289253D4B383404E8C1C' # para encriptación de request, parámetro fijo
        self.llave = '71B9ECE7' # para desencriptar vouchers, parámetro fijo
        self.moneda = 'MXN' # la moneda siempre va a ser en pesos, parámetro fijo
        self.cvvAmex = '' # cuando es american express
        self.response_banco = ''
        self.fecha_consulta = ''
        self.usuario_transaccion = ''

    def obtener_credenciales(self):
        conn = sqlite3.connect('params.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('select * from params')
        param = c.fetchone()
        user , passw = self.desencriptar_credenciales(param['usuario'], param['password'], '')
        self.usuario = user.decode('utf-8')
        self.password = passw.decode('utf-8')       
        #c.execute('''UPDATE params SET usuario=?, password=?''', (user, passw))
        #conn.commit()
        conn.close()

    def encriptar_credenciales(self, usuario, password, key=b'654321'):
        # Usuario
        private_key = hashlib.sha256(key.encode("utf-8")).digest()
        BLOCK_SIZE = 16
        pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
        raw = pad(usuario)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(private_key, AES.MODE_CBC, iv)
        user = base64.b64encode(iv + cipher.encrypt(raw.encode("utf8")))
        user = user.decode('utf-8')
        # Password
        raw = pad(password)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(private_key, AES.MODE_CBC, iv)
        passw = base64.b64encode(iv + cipher.encrypt(raw.encode("utf8")))
        passw = passw.decode('utf-8')
        return user, passw

    def desencriptar_credenciales(self, usuario, password, key=b'654321'):
        private_key = hashlib.sha256(key.encode("utf-8")).digest()
        enc = base64.b64decode(usuario)
        iv = enc[:16]
        cipher = AES.new(private_key, AES.MODE_CBC, iv)
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        user = unpad(cipher.decrypt(enc[16:]))

        enc = base64.b64decode(password)
        iv = enc[:16]
        cipher = AES.new(private_key, AES.MODE_CBC, iv)
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        passw = unpad(cipher.decrypt(enc[16:]))
        return user, passw

    def createxto(self):
        trans3ds = ET.Element('TRANSACTION3DS')
        business = ET.SubElement(trans3ds, 'business')
        ET.SubElement(business, 'bs_idCompany').text = self.compania
        ET.SubElement(business, 'bs_idBranch').text = self.sucursal
        ET.SubElement(business, 'bs_country').text = 'MEX'
        ET.SubElement(business, 'bs_user').text = self.usuario
        ET.SubElement(business, 'bs_pwd').text = self.password
        transaction = ET.SubElement(trans3ds, 'transaction')
        ET.SubElement(transaction, 'tx_merchant').text = self.merchant
        ET.SubElement(transaction, 'tx_reference').text = self.referencia
        ET.SubElement(transaction, 'tx_amount').text = self.importe
        ET.SubElement(transaction, 'tx_currency').text = self.moneda
        creditcard = ET.SubElement(transaction, 'creditcard')
        ET.SubElement(creditcard, 'cc_name').text = self.nombre
        ET.SubElement(creditcard, 'cc_number').text = self.numerotarj
        ET.SubElement(creditcard, 'cc_expMonth').text = self.expmonth
        ET.SubElement(creditcard, 'cc_expYear').text = self.expyear
        ET.SubElement(creditcard, 'cc_cvv').text = self.cvv
        ET.SubElement(transaction, 'tx_urlResponse').text = 'http://127.0.0.1:5000/api/response'
        ET.SubElement(transaction, 'tx_cobro').text = '1'

        mixml = ET.tostring(trans3ds, encoding=None)
        return str(mixml, 'utf-8')

    def crearequest(self, encr):
        encr = str(encr, 'utf-8')
        req = '<pgs><data0>9265654606</data0><data>' + encr + '</data></pgs>'
        return req

    def consume_api(self, texto):
        resp = requests.post('https://qa.mitec.com.mx/ws3dsecure/Auth3dsecure', data={'xml':texto})

        if resp.status_code == 200:
            html_string = resp.text
            return html_string
        else:
            return ('POST /response/{}'.format(response.status_code))
        # consulto en 30 segundos que se haya
        # threading.Timer(interval, function, args = None, kwargs = None)
        timer = threading.Timer(60.0, self.consulta_transacciones())
        timer.start() 
        timer.cancel()
    # esta consulta queda como provisional porque cada banco maneja sus procesos de time out
    # y no será necesario implementarla en producción
    def crea_xml_consulta(self, fecha, referencia):
        consulta = '<user>' + self.usuario + '</user>'
        consulta += '<pwd>' + self.password + '</pwd>'
        consulta += '<id_company>' + self.compania + '</id_company>'
        consulta += '<date>' + fecha + '</date>'
        consulta += '<id_branch>' + self.sucursal + '</id_branch>'
        consulta += '<reference>' + referencia + '</reference>'
        return consulta

    def consulta_transacciones(self, fecha, referencia=None):
        self.obtener_credenciales()
        consulta = self.crea_xml_consulta(fecha, referencia)
        encript = self.encrypt(consulta)
        encript = encript.decode('utf-8')
        client = Client('https://qa3.mitec.com.mx/pgs/services/xmltransacciones?wsdl')
        response = client.service.transacciones('9265654606', encript, '', '', '', '')
        result = self.decrypt(response)
        result = result.decode('utf-8')
        return result

    def encrypt(self, text):
        iv = Random.new().read(AES.block_size)
        decode_hex = codecs.getdecoder("hex_codec")
        key = decode_hex(self.semilla)[0]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        BS = 16
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        padded = pad(text)
        msg = cipher.encrypt(padded.encode('utf8'))
        return base64.b64encode(iv + msg)

    def decrypt(self, text):
        enc = base64.b64decode(text)
        iv = enc[:16]
        decode_hex = codecs.getdecoder("hex_codec")
        key = decode_hex(self.semilla)[0]
        decipher = AES.new(key, AES.MODE_CBC, iv)
        unpad = lambda s : s[:-ord(s[len(s)-1:])]
        return unpad(decipher.decrypt(enc[16:]))

    def KSA(self, key):
        key_length = len(key)
        # create the array "S"
        S = list(range(MOD))  # [0,1,2, ... , 255]
        j = 0
        for i in range(MOD):
            j = (j + S[i] + key[i % key_length]) % MOD
            S[i], S[j] = S[j], S[i]  # swap values

        return S

    def PRGA(self, S):
        i = 0
        j = 0
        while True:
            i = (i + 1) % MOD
            j = (j + S[i]) % MOD

            S[i], S[j] = S[j], S[i]  # swap values
            K = S[(S[i] + S[j]) % MOD]
            yield K

    def get_keystream(self, key):
        S = self.KSA(key)
        return self.PRGA(S)

    def encrypt_logic(self, key, text):
        key = [ord(c) for c in key]

        keystream = self.get_keystream(key)

        res = []
        for c in text:
            val = ("%02X" % (c ^ next(keystream)))  # XOR and taking hex
            res.append(val)
        return ''.join(res)

    def decrypt_voucher(self, text):
        ciphertext = codecs.decode(text, 'hex_codec')
        res = self.encrypt_logic(self.llave, ciphertext)
        return codecs.decode(res, 'hex_codec').decode('utf-8')

    def obtener_response(self, respuesta):
        self.response_banco = self.decrypt(respuesta)
        self.response_banco = self.response_banco.decode('utf-8')
        #print(self.response_banco)
        self.response_banco = self.response_banco.replace("<?xml version='1.0'encoding='UTF-8'?>", '')
        values = ET.fromstring(self.response_banco).findall('.//CENTEROFPAYMENTS')
        for val in values:
            resp = val.find('response').text

            if (resp == 'approved'):
                friend_resp = val.find('friendly_response').text
                numaut = val.find('auth').text
                referencia = val.find('reference').text
                numop = val.find('foliocpagos').text
                fecha = val.find('date').text
                hora = val.find('time').text
                monto = val.find('amount').text
                respuesta2 = 'La transacción fue aprobada: Referencia: {0} Número de Autorización: {1} Número de Operación: {2} Fecha y hora de la transacción: {3} {4} Monto cobrado: {5}'.format(referencia, numaut, numop, fecha, hora, monto)
                print(respuesta2)
                voucher_cliente = val.find('voucher_cliente').text
                voucher_comercio = val.find('voucher_comercio').text
                vouchcl = self.decrypt_voucher(voucher_cliente)
                print(vouchcl)
                vouchco = self.decrypt_voucher(voucher_comercio)
                print(vouchco)
                #return render_template('respuesta.html', respuesta=respuesta2) 
                return respuesta2          
            elif (resp == 'denied'):
                return 'La transacción fue rechazada por el banco emisor'
            else: # es un error
                det_error = val.find('nb_error').text
                print(det_error)
                cod_error = val.find('cd_error').text
                print(cod_error)
                return 'Ocurrió un error al procesar la transacción, no se realizó ningún cargo a la tarjeta. Favor de intentar más tarde'

    def crea_xml_cancelacion(self):
        req = '<?xml version="1.0" encoding="UTF-8"?>'
        req += '<VMCAMEXMCANCELACION>'
        req += '<business>'
        req += '<id_company>' + self.compania + '</id_company>'
        req += '<id_branch>' + self.sucursal + '</id_branch>'
        req += '<country>MEX</country>'
        req += '<user>' + self.usuario + '</user>'
        req += '<pwd>' + self.password + '</pwd>'
        req += '</business>'
        req += '<transacction>'
        req += '<amount>2.00</amount>'
        req += '<no_operacion>300577907</no_operacion>'
        req += '<auth>695298</auth>'
        req += '<usrtransacction>Z703SOAD0</usrtransacction>'
        req += '<crypto>0</crypto>'
        req += '<version>version 11</version>'
        req += '</transacction>'
        req += '</VMCAMEXMCANCELACION>'
        return req


    def cancela_transaccion(self):
        self.obtener_credenciales() # para que obtenga de la base de datos las credenciales desencriptadas
        xml = self.crea_xml_cancelacion()
        xml = self.encrypt(xml)
        texto = self.crearequest(xml)
        #print(texto)
        resp = requests.post('https://qa3.mitec.com.mx/pgs/CancelacionXml', data={'xml':texto})

        if resp.status_code == 200:
            self.response_banco = self.decrypt(resp.text)
            self.response_banco = self.response_banco.decode('utf-8')
            return self.response_banco
        else:
            return ('POST /response/{}'.format(resp.status_code))    

    def validar_informacion(self):
        nombreth = self.nombre
        # que tenga que ingresar su nombre
        if len(nombreth) == 0:
            return 'Debe ingresar su nombre tal como viene en la tarjeta.'
        # que no permita caracteres especiales
        if nombreth.isalpha() == True:
            return 'No se permiten caracteres especiales en su nombre.'
        # no se permiten números en el nombre del TH
        match = re.match(r'^[A-Za-z ]*$', nombreth )
        if not match:
            return 'No se permiten números en su nombre. Favor de verificar'

        # valida la cantidad de numeros de las tarjetas
        numtarj = self.numerotarj
        if numtarj[1] == 3: #es american express
            if len(numtarj) > 15 or len(numtarj) < 15:
                return 'No es correcta la cantidad de números de su tarjeta.'
        else: # master card, visa o discover
            if len(numtarj) > 16 or len(numtarj) < 16:
                return 'No es correcta la cantidad de números de su tarjeta.'
        # que no permita caracteres especiales
        if nombreth.isalpha() == True:
            return 'No se permiten caracteres especiales en el número de la tarjeta.'
        # no se permiten letras en el número de tarjeta
        if numtarj.isnumeric():
            return 'No se permiten letras en el número de tarjeta. Favor de verificar'           


# prueba del request
# req = PagoSinTarjeta()
# req.compania = 'Z703'
# req.sucursal = '210'
# req.referencia = 'GOC12372' # Muy necesario poner siglas de hotel para que no se vaya 
# # a colicionar con otro numero de reserva igual de otro hotel
# req.importe = '3000'
# req.nombre = 'ALEJANDRO GONZALEZ'
# req.numerotarj = '4111111111111111'
# req.expmonth = '04'
# req.expyear = '20'
# req.cvv = '123'
# req.obtener_credenciales() 
# texto = req.createxto()
# #print(texto)
# encrypted = req.encrypt(texto)
# #print('Encrypted: %s' % encrypted)
# encrip = req.crearequest(encrypted)
# print(encrip)
# request = req.consume_api(encrip)
# print(request)
# req = PagoSinTarjeta()
# decrypted = req.decrypt('QJRwCRMDfNyIC2AlZDxzNNCR1DgEHWE+rGBYHRgl2VwYG2EWShrAvx6/4WmeBtPZleB7mGnZUnTMRKmqjcUFZHoUS0Sp+SVU7vQ9iWolpLqREznMhtqqyEdWmbONflI/JNK9U7R8eJFBu2Uc6x9PNjKjv/WonbBFTzxwWgWCWWLUapZ/KStc/9gBQWUi2nMqqjP631lmAjhatk/bTbCGn0P6q2jhC2jH/lUsCjuCq5HDuABqVKwhbj3vALlNWt48GXk7P7Nqv7GuFyIRTLJKrf2Mp6FFRoD1CAnd4H66j9vZgi1pKqT9feu3/85hglE27UBcHLbYDWWFEdoQChVqyug0YiDZfyOxO5OC29xOfOwi8QItZsI3MyNqwjMRSCkfMLK5KAZKAOWvtnpBIZMgcwFC7gpggnWop4Jire9QwZ6KWyC92CQQvZAaf9ozTITmTwnRNcfifLDaUc7gt8bfTmK1/3y5M1C2HbaHV+5bJ8w3r9scFEw4bFNjpnpdAPtMLchnC7REPPzQPCSm968jORPC92CZR7XsfLY+neuz8V4mx1wW7o56sYf+fwLwXGGhRqARS0M+MlCDIfRBFKg35iPvRwoxO9mYDHYWSpJ50OsJwqjmtVWjA/m/xEEI4E9zZj1cjFXk1xiriXXd0jSUfyYwyzB49aYD9fawCYEVczH6P9jkTBh8dHvWFVaY5D19wNfMVHnRbgtaTg9RZKqMVQ0SFpwPM8eWC+qqQqUi12X99JeFORLBlneZJ+Brwp/BIPXvbsQ40ISlGdeQSu6ZPnxUj6Nh9bhv2PStXP/F947Wo5/0a/VZQO72s1KviPxMxsPvUW/wWCzbIZA9/GoQ/PXASDXsv+sWdPnd9xlGsUzfOt+38FNnrrWL/R/es+GCOmWB9UqBAC2fPuzFpSRNHtxxyzU91T213fXnp9VDSMnMDxRn4803q9DMVhKIUnEbs5jZgO+3xAINclLrzYRC1lrbQgkdWfIqjN2a5FZ6PzhMZ/ojrvH5h/XSyR9U5PBWIYxxCfoS4CjG++2dCVranjjL9/jXU1R97/76S5yyzXmS13PiP2vYWewWAb4AYxvUwYFBZxldNx9c0FsI2D//PA==')
# print(decrypted)
# req = PagoSinTarjeta()
# decrypted = req.decrypt_voucher('')
# print(decrypted)
# req = PagoSinTarjeta()
# user, passw = req.encriptar_credenciales('Z703SOUS0', '8ROOEJVYS4', '')
# print(user)
# print(passw)
# req = PagoSinTarjeta()
# transacciones = req.consulta_transacciones('07/03/2019', '')
# print(transacciones)
# req = PagoSinTarjeta()
# respuesta = req.cancela_transaccion()
# print(respuesta)