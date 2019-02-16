from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
import requests, base64, codecs
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import tostring

class PagoSinTarjeta(object):
    def __init__(self,usuario,password):
        self.usuario = usuario
        self.password = password
        self.compania = 'Z703'
        self.sucursal = '210'
        self.referencia = 'GOC123580'
        self.importe = '1500'
        self.key_bytes = 16 #(AES128)
        self.merchant = '158198' # Siempre va a ser de contado
        self.nombre = ''
        self.numerotarj = ''
        self.expmonth = ''
        self.expyear = ''
        self.codamex = ''
        self.cvv = ''
        self.semilla = 'A2832DE3C0B2289253D4B383404E8C1C'

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
        ET.SubElement(transaction, 'tx_currency').text = 'MXN'
        creditcard = ET.SubElement(transaction, 'creditcard')
        ET.SubElement(creditcard, 'cc_name').text = self.nombre
        ET.SubElement(creditcard, 'cc_number').text = self.numerotarj
        ET.SubElement(creditcard, 'cc_expMonth').text = self.expmonth
        ET.SubElement(creditcard, 'cc_expYear').text = self.expyear
        ET.SubElement(creditcard, 'cc_cvv').text = self.cvv
        ET.SubElement(transaction, 'tx_urlResponse').text = 'http://192.168.2.51:5000/api/response'
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

    def r_pad(payload, block_size=16):
        length = block_size - (len(payload) % block_size)
        return payload + chr(length) * length

# prueba del request
# req = PagoSinTarjeta('Z703SOUS0','8ROOEJVYS4')
# req.compania = 'Z703'
# req.sucursal = '210'
# req.referencia = 'GOC12370' # Muy necesario poner siglas de hotel para que no se vaya 
# # a colicionar con otro numero de reserva igual de otro hotel
# req.importe = '3000'
# req.nombre = 'ALEJANDRO GONZALEZ'
# req.numerotarj = '4111111111111111'
# req.expmonth = '04'
# req.expyear = '20'
# req.cvv = '123' 
# texto = req.createxto()
# #print(texto)
# encrypted = req.encrypt(texto)
# #print('Encrypted: %s' % encrypted)
# encrip = req.crearequest(encrypted)
# #print(encrip)
# request = req.consume_api(encrip)
# print(request)
# req = PagoSinTarjeta('','')
# decrypted = req.decrypt('owFf92LdAZu0GCwoSzWoPc7O09Cm3XqJ0+J2GCxjkq4BImcmYNiluJaokRIsEbypTinq7XehdkRoxASb3mHD0CG1SjyqRdz61X/FAxELB50Ykly/WkT6WnwDUc3hv7S493kWlpcuEwB8bJ1t9TtXV4ySIj00IU3AkzfxqEuOQd1gkwxrp0Ol/vFZ5ftrGftMZFJCpSWqtFImHOcTGgqHzWLDCW8WTqcMlAZzzU0rJ8b4FIqbkksCeUtq0hi32UA6PDyScnqnyBQLK8xqfbPmmu5wnQEBZyIBHWQpiN0XDvwI1F/8TsTRef1wZqPKJMzI5GU9UIzthls+XSUXYIP6XaETYyBS8dAKgqub8rvEP3FBK+RL6T5z6Ck/ANorv56ASY/qv+7YTXNAm1T9kjB8avRxXBxbL5eNRYkMmb+iBV0ecmEY5NL0jL2FPxW0Vb+p434InbAdmpjtKIGUCc8EiOAXUcluGAxPV40nveAWVZ5qjosLxvh4mBmdmxR6Dt1ulibJztC/cq/7Ksf8jCkNNBOTPCXuuk8Y0ch7qmu+d2j3axr7+4Fp0ZKNIRmCYu9uAjkj27TJPESUQyoIZ/iPngflfWG7Jrm+MpTwbQsUgyUB/Jsu9U+uEnfVY71I2cW6YuqtSkLTtuYDryxRJ1pihVmBKfw/4NMgka7mTK4lamILt8HoeZzHz1vYSlofJ2g9RfVPpn/Q8ojACtftYZdLFIrtAygEGwDBPQWAcIm8sU+FdDoBj84S+bhTk3am0mLGq3xSL4qaMs4JTG7KU8QDK1p8JVsAo6E+z6Tpk5MAdGmiwp+IW/7xTA6b67Ioqo92+1yh2YQbtVj/mcG0n4X8Lvdy/qV+KGTrDeAvBw9d1K64gNwv6by0eq95QttSGTZjuqpZ1eVDDpuABZXLpDaH+topRayXz7TAtQ3T8G5tXKKHb4WMDzwuz1w2Z0NIr4jE1blCmo/75HvIPKA9E7pLcxXRHSQO9nIVhvjqGDJkZhc1Z17DsAqp48EFMyLxk6C0AOga/8Rh5rPWX6huzVEQR9eU8TazMBBD3+pgvOy3hpA/38QNqOQ0boD9eUmoTYjDCMbjGtY2HcouMwnayRUQZc194Xuhg1CCIXfVZWO5qsY6J5xc72ODKz1dfwyOAaTBe3LQwk1GEdfhnGlZlp35zcH4J+KSIPjnoyWaILApJR50OGfiRP3oj/P8RXRoJK3Wl3Z9O2j5dvFM2iEq2ynAeA==')
# print(decrypted)