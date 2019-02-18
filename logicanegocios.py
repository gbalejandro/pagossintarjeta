from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random
import requests, base64, codecs
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import tostring
from arc4 import ARC4
from hashlib import sha1

MOD = 256

class PagoSinTarjeta(object):
    def __init__(self,usuario,password):
        self.usuario = usuario
        self.password = password
        self.compania = 'Z703'
        self.sucursal = '210'
        self.referencia = 'GOC123595'
        self.importe = '0.1'
        self.key_bytes = 16 #(AES128)
        self.merchant = '158198' # Siempre va a ser de contado
        self.nombre = ''
        self.numerotarj = ''
        self.expmonth = ''
        self.expyear = ''
        self.codamex = ''
        self.cvv = ''
        self.semilla = 'A2832DE3C0B2289253D4B383404E8C1C'
        self.llave = '71B9ECE7'

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
# decrypted = req.decrypt('48B322D72CADD416C11A583DA509FF61A8278CCD30046081496BCF1BBEE78B7B4EAEFDB0F485950FDB829E05633A652052EC09A1AA421733896C6E2088A267DB69B3AD6E58762DF6262E6243964FFC014D98BFE82171329918ABCE9530D0159877FE799691B2964738EA7F0D3B5BCB39E5755A25BF2DC19EA7DDCA937BC477DBC92A70F57DAE1E3A28B280B02CB33D36294EC1075E492B93CF9666428C16FFBDA7FCDBB7E3AED13CDDA42AB820D670129DFD498D102A50C9C019772A9586B1721B149FC80EE7215AF6BAC4A622A3B9A67D2A00517C3B31A8166352B00240014D3D938BA3A7610E133BC7F5D770147AB02E2454ACC111E28BF377C222FBA9476E48084ED5315356DDD317012D7496674A003707112474800F234474B96ED90723F93E597002A727654B5268FFF1ECCBE47939304F2A62806C0DFD57615D562554F57B26EC8A067A00FC943DFAD76A125D484676E4CE4C2516F7D053F6830194EC97BF297E68BBA946C74A04DFCB41F4CAED7DBC29FD3B092205186AE247EC138FA2AF57E237AE39E01FE0341253EC7AC3E61D09816C4BEAC3AA1B13D3D891EE1F3B9E7A31CC742E1B0E105A50A6FD1695380B7CCDE52BF4923F1DA0F03C250C72E4B1844074EF6E227C81CA79EF9E7203198453AC53D6260E6319B203CECA7BE9C92E64856182A73A5DBDF10370AD2865A094689CFCB5D3221CFA63810362EF6ED37A6F131E1051603FE70CA4FB74BF806746352292BCD44DA5D3581A2E88E2F0895ACC3F0E25532300795A78E0EAEDAC8C76B20FA0F6FCBF0CBBEBF4A8EE79C3BEF587918C3696CBC69B8C553EF8EAD659D19A22593459B622AC9C11177DEBE5231BFB01D779838246371F65AAE4DAD4DDE6FAFA31B2D113403A55AF2D215094AEFA771FA03C12C9BB0D8FE3C8554D7E16926F5AC27FC06B3F6264B49434971F99C452653F62C1215BBA977EC176F8F342045C80A5D7A9E6B931455DF33B13A0BCB51E370D45D0297291B9F5D8B3D48B47E6270A64810CFC6D7F7DA8E38FB6814D2346DBCA8F8159009D8DE100F4F357F4152972263F837566BEC3A1C2C0564CBF96C803B8B404B7C4B5292671D72711462A30D26E19F22303D30706C8861CF5E9360B7540DA792A8F4BE0040E532B2620182B39ABD92E14B913B32B69EA1B28674AE40A1A92D2232C4D093C41DEB829BA7C59B39485B9BA2E6748990FDCB49E54A51C8D10607F10F43D92007F1BF70DFA2865A04085B74AE780CA61463B94330500AD78A1CC32B5E23C47AA8612C8B29DF461BA1BD340DAD94FCCD720810D9E5325FFEC489F25BCF6D986D3163B8D3D0E1D0DB553D52808E49C2E83816E7C5AC83D9E2497A8716ABA9A44CCE6B268716AA5C9CD6B32C8581FA8C30A66FB1DA66DA0533B38ADC6441F7464AD74AFB7954561C2F4486A56E3E8C39BE843CC102A7964C889A2B88C41E201DEC9A11B10E0B68AE73716A787305F4079236BB247B237609BDD97DDA922C281F2AAF260C87924A07CAF3337BB3FBD83D822E42BEDFB418BBC594C83A539662D52CDC810CC1746F453A1F059F1301D5561BF155A562CF93DA52E164C5BAB33800DE6E9F0B371FB1D1338E957CA6ED87D93F9E37FB16618802820F599A2C15B048CFB7BB8A4909D2EA19E07726D02DB4D92734E3EC9BEDA07D027DE14C3467754E773CDD1EBE2F54AFDE580C6EF6F991FA63078349914871DFE7BBABCE4BDBA53183EF81FCAE8AC2E0897E063F1A469C3ECAAAEB87E54AF1DE59871C0C47DFE0F44D1FC9190B7CB723205B11CC6388CD6F52ACB00006903D37664B7E5781FFA761234B5FCCB0D24028C3059D6A58F247852D2F2D7B73D7FD7403FD3F510C18443D94F2E401EB87502B1523DC1806B6F28A756F6BF175848AB79A3F002938AA470AD512F323E23AD4709DB35C51611D59A79E7C901ADEE260CCB733701D22F2D73')
# print(decrypted)
# req = PagoSinTarjeta('','')
# decrypted = req.decrypt_voucher('48B322D72CADD416C11A583DA509FF61A8278CCD30046081496BCF1BBEE78B7B4EAEFDB0F485950FDB829E05633A652052EC09A1AA421733896C6E2088A267DB69B3AD6E58762DF6262E6243964FFC014D98BFE82171329918ABCE9530D0159877FE799691B2964738EA7F0D3B5BCB39E5755A25BF2DC19EA7DDCA937BC477DBC92A70F57DAE1E3A28B280B02CB33D36294EC1075E492B93CF9666428C16FFBDA7FCDBB7E3AED13CDDA42AB820D670129DFD498D102A50C9C019772A9586B1721B149FC80EE7215AF6BAC4A622A3B9A67D2A00517C3B31A8166352B00240014D3D938BA3A7610E133BC7F5D770147AB02E2454ACC111E28BF377C222FBA9476E48084ED5315356DDD317012D7496674A003707112474800F234474B96ED90723F93E597002A727654B5268FFF1ECCBE47939304F2A62806C0DFD57615D562554F57B26EC8A067A00FC943DFAD76A125D484676E4CE4C2516F7D053F6830194EC97BF297E68BBA946C74A04DFCB41F4CAED7DBC29FD3B092205186AE247EC138FA2AF57E237AE39E01FE0341253EC7AC3E61D09816C4BEAC3AA1B13D3D891EE1F3B9E7A31CC742E1B0E105A50A6FD1695380B7CCDE52BF4923F1DA0F03C250C72E4B1844074EF6E227C81CA79EF9E7203198453AC53D6260E6319B203CECA7BE9C92E64856182A73A5DBDF10370AD2865A094689CFCB5D3221CFA63810362EF6ED37A6F131E1051603FE70CA4FB74BF806746352292BCD44DA5D3581A2E88E2F0895ACC3F0E25532300795A78E0EAEDAC8C76B20FA0F6FCBF0CBBEBF4A8EE79C3BEF587918C3696CBC69B8C553EF8EAD659D19A22593459B622AC9C11177DEBE5231BFB01D779838246371F65AAE4DAD4DDE6FAFA31B2D113403A55AF2D215094AEFA771FA03C12C9BB0D8FE3C8554D7E16926F5AC27FC06B3F6264B49434971F99C452653F62C1215BBA977EC176F8F342045C80A5D7A9E6B931455DF33B13A0BCB51E370D45D0297291B9F5D8B3D48B47E6270A64810CFC6D7F7DA8E38FB6814D2346DBCA8F8159009D8DE100F4F357F4152972263F837566BEC3A1C2C0564CBF96C803B8B404B7C4B5292671D72711462A30D26E19F22303D30706C8861CF5E9360B7540DA792A8F4BE0040E532B2620182B39ABD92E14B913B32B69EA1B28674AE40A1A92D2232C4D093C41DEB829BA7C59B39485B9BA2E6748990FDCB49E54A51C8D10607F10F43D92007F1BF70DFA2865A04085B74AE780CA61463B94330500AD78A1CC32B5E23C47AA8612C8B29DF461BA1BD340DAD94FCCD720810D9E5325FFEC489F25BCF6D986D3163B8D3D0E1D0DB553D52808E49C2E83816E7C5AC83D9E2497A8716ABA9A44CCE6B268716AA5C9CD6B32C8581FA8C30A66FB1DA66DA0533B38ADC6441F7464AD74AFB7954561C2F4486A56E3E8C39BE843CC102A7964C889A2B88C41E201DEC9A11B10E0B68AE73716A787305F4079236BB247B237609BDD97DDA922C281F2AAF260C87924A07CAF3337BB3FBD83D822E42BEDFB418BBC594C83A539662D52CDC810CC1746F453A1F059F1301D5561BF155A562CF93DA52E164C5BAB33800DE6E9F0B371FB1D1338E957CA6ED87D93F9E37FB16618802820F599A2C15B048CFB7BB8A4909D2EA19E07726D02DB4D92734E3EC9BEDA07D027DE14C3467754E773CDD1EBE2F54AFDE580C6EF6F991FA63078349914871DFE7BBABCE4BDBA53183EF81FCAE8AC2E0897E063F1A469C3ECAAAEB87E54AF1DE59871C0C47DFE0F44D1FC9190B7CB723205B11CC6388CD6F52ACB00006903D37664B7E5781FFA761234B5FCCB0D24028C3059D6A58F247852D2F2D7B73D7FD7403FD3F510C18443D94F2E401EB87502B1523DC1806B6F28A756F6BF175848AB79A3F002938AA470AD512F323E23AD4709DB35C51611D59A79E7C901ADEE260CCB733701D22F2D73')
# print(decrypted)