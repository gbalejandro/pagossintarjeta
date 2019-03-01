// var visa = /^4[0-9]{12}(?:[0-9]{3})?$/;//All Visa card numbers start with a 4. New cards have 16 digits. Old cards have 13.
// var masterCard = /^5[1-5][0-9]{14}$/;//All MasterCard numbers start with the numbers 51 through 55. All have 16 digits.
// var amex = /^3[47][0-9]{13}$/;//American Express card numbers start with 34 or 37 and have 15 digits.
// var discover = /^6(?:011|5[0-9]{2})[0-9]{12}$/;//Discover card numbers begin with 6011 or 65. All have 16 digits.
// var emails =  /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
// var cvv = /^[0-9]{3,4}/;//Credit cards security code. from 3 to 4 digits

var intervalId = 0;

function updateIsFinished()
{
    $('input[type="submit"]:nth-child(2)').trigger('click');
}

$(document).ready(function(){
    $('#btnEnviar').click(function(event){
        $.ajax({
            url: 'postmethod',
            type: 'POST',
            dataType: 'json',
            data: {nombre:$('#nombre').val(),
                   numero:$('#numero').val(),
                   mes:$('#mes').val(),
                   anio:$('#anio').val(),
                   cvv:$('#cvv').val()
            },
            success:function(response)
            {
                console.log(response);
                window.location.href = '/api/redirige';
            },
            error: function (error) {
                console.log(error);
            }
            
        });
    });
    // verifico si es american express o visa/master card
    $("#numero").focusout(function() {
        var numero = $("#numero").val();
        if (numero.substring(0, 1) == 3){
            // valido que nada mas permita 15 números
            if (numero.length > 15 || numero.length < 15){
                alert("La cantidad de números de este tipo de tarjeta no es la correcta.");
                $("#numero").focus();
                return false;
            }
            else {
                $("#txtAmex").show();
            }            
        } 
        else {
            if (numero.length > 16 || numero.length < 16){
                alert("La cantidad de números de este tipo de tarjeta no es la correcta.");
                //$("#numero").focus();
                return false;
            }            
        }
    });
    // para el campo nombre del TH sólo permite letras y espacios
    $("#nombre").keypress(function (key) {
        window.console.log(key.charCode)
        if ((key.charCode < 97 || key.charCode > 122)//letras mayusculas
            && (key.charCode < 65 || key.charCode > 90) //letras minusculas
            && (key.charCode != 45) //retroceso
            && (key.charCode != 241) //ñ
             && (key.charCode != 209) //Ñ
             && (key.charCode != 32) //espacio
             && (key.charCode != 225) //á
             && (key.charCode != 233) //é
             && (key.charCode != 237) //í
             && (key.charCode != 243) //ó
             && (key.charCode != 250) //ú
             && (key.charCode != 193) //Á
             && (key.charCode != 201) //É
             && (key.charCode != 205) //Í
             && (key.charCode != 211) //Ó
             && (key.charCode != 218) //Ú

            )
            return false;
    });
});