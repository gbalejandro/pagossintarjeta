from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
import requests, base64, codecs, sqlite3, hashlib, re
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import tostring
from arc4 import ARC4

MOD = 256

class PagoSinTarjeta(object):
    def __init__(self):
        self.usuario = ''
        self.password = ''
        self.compania = 'Z703'
        self.sucursal = '210'
        self.referencia = 'GOC12619'
        self.importe = '0.01'
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
        response1 = self.decrypt(respuesta)
        response1 = response1.decode('utf-8')
        print(response1)
        response1 = response1.replace("<?xml version='1.0'encoding='UTF-8'?>", '')
        values = ET.fromstring(response1).findall('.//CENTEROFPAYMENTS')
        for val in values:
            resp = val.find('response').text

            if (resp == 'approved'):
                friend_resp = val.find('friendly_response').text
                numaut = val.find('auth').text
                respuesta2 = 'Su transacción ha sido ' + friend_resp + ' con el número de autorización ' + numaut
                referencia = val.find('reference').text
                voucher_cliente = val.find('voucher_cliente').text
                voucher_comercio = val.find('voucher_comercio').text
                vouchcl = self.decrypt_voucher(voucher_cliente)
                print(vouchcl)
                vouchco = self.decrypt_voucher(voucher_comercio)
                print(vouchco)
                #return render_template('respuesta.html', respuesta=respuesta2) 
                return respuesta2          
            elif (resp == 'denied'):
                respuesta2 = 'La transacción fue rechazada por el banco emisor'
                #return render_template('respuesta.html', respuesta=resp)
                return respuesta2
            else: # es un error
                det_error = val.find('nb_error').text
                cod_error = val.find('cd_error').text
                respuesta2 = 'Ocurrió un error al procesar la transacción, no se realizó ningún cargo a la tarjeta. Favor de intentar más tarde'
                #return render_template('respuesta.html', respuesta=error)
                return respuesta2

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
# print(encrip)
# request = req.consume_api(encrip)
# print(request)
# req = PagoSinTarjeta('','')
# decrypted = req.decrypt('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')
# print(decrypted)
# req = PagoSinTarjeta('','')
# decrypted = req.decrypt_voucher('48B322D72CADD416C11A583DA509FF61A8278CCD30046081496BCF1BBEE78B7B4EAEFDB0F485950FDB829E05633A652052EC09A1AA421733896C6E2088A267DB69B3AD6E58762DF6262E6243964FFC014D98BFE82171329918ABCE9530D0159877FE799691B2964738EA7F0D3B5BCB39E5755A25BF2DC19EA7DDCA937BC477DBC92A70F57DAE1E3A28B280B02CB33D36294EC1075E492B93CF9666428C16FFBDA7FCDBB7E3AED13CDDA42AB820D670129DFD498D102A50C9C019772A9586B1721B149FC80EE7215AF6BAC4A622A3B9A67D2A00517C3B31A8166352B00240014D3D938BA3A7610E133BC7F5D770147AB02E2454ACC111E28BF377C222FBA9476E48084ED5315356DDD317012D7496674A003707112474800F234474B96ED90723F93E597002A727654B5268FFF1ECCBE47939304F2A62806C0DFD57615D562554F57B26EC8A067A00FC943DFAD76A125D484676E4CE4C2516F7D053F6830194EC97BF297E68BBA946C74A04DFCB41F4CAED7DBC29FD3B092205186AE247EC138FA2AF57E237AE39E01FE0341253EC7AC3E61D09816C4BEAC3AA1B13D3D891EE1F3B9E7A31CC742E1B0E105A50A6FD1695380B7CCDE52BF4923F1DA0F03C250C72E4B1844074EF6E227C81CA79EF9E7203198453AC53D6260E6319B203CECA7BE9C92E64856182A73A5DBDF10370AD2865A094689CFCB5D3221CFA63810362EF6ED37A6F131E1051603FE70CA4FB74BF806746352292BCD44DA5D3581A2E88E2F0895ACC3F0E25532300795A78E0EAEDAC8C76B20FA0F6FCBF0CBBEBF4A8EE79C3BEF587918C3696CBC69B8C553EF8EAD659D19A22593459B622AC9C11177DEBE5231BFB01D779838246371F65AAE4DAD4DDE6FAFA31B2D113403A55AF2D215094AEFA771FA03C12C9BB0D8FE3C8554D7E16926F5AC27FC06B3F6264B49434971F99C452653F62C1215BBA977EC176F8F342045C80A5D7A9E6B931455DF33B13A0BCB51E370D45D0297291B9F5D8B3D48B47E6270A64810CFC6D7F7DA8E38FB6814D2346DBCA8F8159009D8DE100F4F357F4152972263F837566BEC3A1C2C0564CBF96C803B8B404B7C4B5292671D72711462A30D26E19F22303D30706C8861CF5E9360B7540DA792A8F4BE0040E532B2620182B39ABD92E14B913B32B69EA1B28674AE40A1A92D2232C4D093C41DEB829BA7C59B39485B9BA2E6748990FDCB49E54A51C8D10607F10F43D92007F1BF70DFA2865A04085B74AE780CA61463B94330500AD78A1CC32B5E23C47AA8612C8B29DF461BA1BD340DAD94FCCD720810D9E5325FFEC489F25BCF6D986D3163B8D3D0E1D0DB553D52808E49C2E83816E7C5AC83D9E2497A8716ABA9A44CCE6B268716AA5C9CD6B32C8581FA8C30A66FB1DA66DA0533B38ADC6441F7464AD74AFB7954561C2F4486A56E3E8C39BE843CC102A7964C889A2B88C41E201DEC9A11B10E0B68AE73716A787305F4079236BB247B237609BDD97DDA922C281F2AAF260C87924A07CAF3337BB3FBD83D822E42BEDFB418BBC594C83A539662D52CDC810CC1746F453A1F059F1301D5561BF155A562CF93DA52E164C5BAB33800DE6E9F0B371FB1D1338E957CA6ED87D93F9E37FB16618802820F599A2C15B048CFB7BB8A4909D2EA19E07726D02DB4D92734E3EC9BEDA07D027DE14C3467754E773CDD1EBE2F54AFDE580C6EF6F991FA63078349914871DFE7BBABCE4BDBA53183EF81FCAE8AC2E0897E063F1A469C3ECAAAEB87E54AF1DE59871C0C47DFE0F44D1FC9190B7CB723205B11CC6388CD6F52ACB00006903D37664B7E5781FFA761234B5FCCB0D24028C3059D6A58F247852D2F2D7B73D7FD7403FD3F510C18443D94F2E401EB87502B1523DC1806B6F28A756F6BF175848AB79A3F002938AA470AD512F323E23AD4709DB35C51611D59A79E7C901ADEE260CCB733701D22F2D73')
# print(decrypted)
# req = PagoSinTarjeta()
# user, passw = req.encriptar_credenciales('Z703SOUS0', '8ROOEJVYS4', '')
# print(user)
# print(passw)