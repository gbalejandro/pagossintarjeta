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
        #consulta = self.crea_xml_consulta(fecha, referencia)
        client = Client('https://qa3.mitec.com.mx/pgs/services/xmltransacciones?wsdl')
        response = client.service.transacciones(in0=self.usuario, in1=self.password, in2=self.compania, in3=fecha, in4=self.sucursal, in5=referencia)
        return response

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
# decrypted = req.decrypt('2866756e6374696f6e2829207b0d0a2066756e6374696f6e2067657453657373696f6e436f6f6b6965732829207b0d0a0976617220636f6f6b69654172726179203d206e657720417272617928293b0d0a0976617220634e616d65203d206e65772052656745787028275e5c5c733f696e6361705f7365735f27293b0d0a097661722063203d20646f63756d656e742e636f6f6b69652e73706c697428223b22293b0d0a09666f7220287661722069203d20303b2069203c20632e6c656e6774683b20692b2b29207b0d0a0909766172206b6579203d20635b695d2e73756273747228302c20635b695d2e696e6465784f6628223d2229293b0d0a09097661722076616c7565203d20635b695d2e73756273747228635b695d2e696e6465784f6628223d2229202b20312c20635b695d2e6c656e677468293b0d0a090969662028634e616d652e74657374286b65792929207b0d0a090909636f6f6b696541727261795b636f6f6b696541727261792e6c656e6774685d203d2076616c75653b0d0a09097d0d0a097d0d0a0972657475726e20636f6f6b696541727261793b0d0a207d0d0a2066756e6374696f6e20736574496e636170436f6f6b69652876417272617929207b0d0a09766172207265733b0d0a09747279207b0d0a090976617220636f6f6b696573203d2067657453657373696f6e436f6f6b69657328293b0d0a09097661722064696765737473203d206e657720417272617928636f6f6b6965732e6c656e677468293b0d0a0909666f7220287661722069203d20303b2069203c20636f6f6b6965732e6c656e6774683b20692b2b29207b0d0a090909646967657374735b695d203d2073696d706c6544696765737428764172726179202b20636f6f6b6965735b695d293b0d0a09097d0d0a0909726573203d20764172726179202b20222c6469676573743d22202b20646967657374732e6a6f696e28293b0d0a097d20636174636820286529207b0d0a0909726573203d20764172726179202b20222c6469676573743d22202b20656e636f6465555249436f6d706f6e656e7428652e746f537472696e672829293b0d0a097d0d0a09637265617465436f6f6b696528225f5f5f75746d7663222c207265732c203230293b0d0a207d0d0a2066756e6374696f6e2073696d706c65446967657374286d7973747229207b0d0a0976617220726573203d20303b0d0a09666f7220287661722069203d20303b2069203c206d797374722e6c656e6774683b20692b2b29207b0d0a0909726573202b3d206d797374722e63686172436f646541742869293b0d0a097d0d0a0972657475726e207265733b0d0a207d0d0a2066756e6374696f6e20637265617465436f6f6b6965286e616d652c2076616c75652c207365636f6e647329207b0d0a097661722065787069726573203d2022223b0d0a09696620287365636f6e647329207b0d0a09097661722064617465203d206e6577204461746528293b0d0a0909646174652e73657454696d6528646174652e67657454696d652829202b20287365636f6e6473202a203130303029293b0d0a09097661722065787069726573203d20223b20657870697265733d22202b20646174652e746f474d54537472696e6728293b0d0a097d0d0a09646f63756d656e742e636f6f6b6965203d206e616d65202b20223d22202b2076616c7565202b2065787069726573202b20223b20706174683d2f223b0d0a207d0d0a2066756e6374696f6e2074657374286f29207b0d0a0976617220726573203d2022223b0d0a0976617220764172726179203d206e657720417272617928293b0d0a09666f722028766172206a203d20303b206a203c206f2e6c656e6774683b206a2b2b29207b0d0a09207661722074657374203d206f5b6a5d5b305d3b0d0a092073776974636820286f5b6a5d5b315d29207b0d0a092009636173652022657869737473223a0d0a0909747279207b0d0a090909696628747970656f66286576616c2874657374292920213d3d2022756e646566696e656422297b0d0a090909097641727261795b7641727261792e6c656e6774685d203d20656e636f6465555249436f6d706f6e656e742874657374202b20223d7472756522293b0d0a0909097d0d0a090909656c73657b0d0a090909097641727261795b7641')
# print(decrypted)
# req = PagoSinTarjeta()
# decrypted = req.decrypt_voucher('')
# print(decrypted)
# req = PagoSinTarjeta()
# user, passw = req.encriptar_credenciales('Z703SOUS0', '8ROOEJVYS4', '')
# print(user)
# print(passw)
# req = PagoSinTarjeta()
# transacciones = req.consulta_transacciones('07/03/2019', 'GOC12623')
# print(transacciones)
# req = PagoSinTarjeta()
# respuesta = req.cancela_transaccion()
# print(respuesta)