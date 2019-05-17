// var visa = /^4[0-9]{12}(?:[0-9]{3})?$/;//All Visa card numbers start with a 4. New cards have 16 digits. Old cards have 13.
// var masterCard = /^5[1-5][0-9]{14}$/;//All MasterCard numbers start with the numbers 51 through 55. All have 16 digits.
// var amex = /^3[47][0-9]{13}$/;//American Express card numbers start with 34 or 37 and have 15 digits.
// var discover = /^6(?:011|5[0-9]{2})[0-9]{12}$/;//Discover card numbers begin with 6011 or 65. All have 16 digits.
// var emails =  /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
// var cvv = /^[0-9]{3,4}/;//Credit cards security code. from 3 to 4 digits
//import bust from 'gulp-cache-bust'

var intervalId = 0;

function updateIsFinished()
{
    $('input[type="submit"]:nth-child(2)').trigger('click');
}

$(document).ready(function(){
    $("#nombre").focus();
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

    $('#cvv').focusout(function(){
        var codigo = $("#cvv").val();
        // reviso que el cliente no ponga 3 ceros solo en V/MC o Discover
        if (numero.substring(0, 1) != 3){
            if (codigo.search('000') != -1){
                $("#mensajecvv").html("No puede ingresar únicamente ceros. Favor de verificar.")
                $("#cvv").focus();
                $("#cvv").select();
                return;
            }
            else {
                $("#mensajecvv").html("");
                $("#btnEnviar").click();
            }
        }
    });

    $("#nombre").focusout(function() {
        var nombre = $("#nombre").val();
        if (nombre.length == 0){
            $("#mensajeno").html("Es necesario que ingrese el nombre tal cual viene en la tarjeta.");
            setTimeout(function() {
                $("#nombre").focus();
                $("#nombre").select();
            }, 5)            
        }
        else{
            $("#mensajeno").html("");
        }
    });

    $("#numero").focusout(function() {
        var numero = $("#numero").val();
        // verifico la cantidad de numeros por tarjeta
        if (numero.substring(0, 1) == 3){
            // valido que nada mas permita 15 números
            if (numero.length > 15 || numero.length < 15){
                $("#mensajenu").html("Favor de ingresar la cantidad de números indicados para esta tarjeta");
                setTimeout(function() {
                    $("#numero").focus();
                    $("#numero").select();
                }, 10)
            }
            else {
                $("#mensajenu").html("");
            } 
            // valido el código de verificación
            var cvvA = $("#cvv").val();
            if (cvvA.length > 4 || cvvA.length < 4){
                $("#mensajecvv").html("Favor de ingresar los dígitos correctos para el código de verificación.")
                setTimeout(function() {
                    $("#mensajecvv").focus();
                    $("#mensajecvv").select();
                }, 10);
            }
            else{
                $("#mensajecvv").html("");
            }           
        } 
        else {
            if (numero.length > 16 || numero.length < 16){
                $("#mensajenu").html("Favor de ingresar la cantidad de números indicados para esta tarjeta");
                setTimeout(function() {
                    $("#numero").focus();
                    $("#numero").select();
                }, 5)
            }
            else {
                $("#mensajenu").html("");
            } 
            // valido el código de verificación
            var cvvA = $("#cvv").val();
            if (cvvA.length > 3 || cvvA.length < 3){
                $("#mensajecvv").html("Favor de ingresar los dígitos correctos para el código de verificación.")
                setTimeout(function() {
                    $("#mensajecvv").focus();
                    $("#mensajecvv").select();
                }, 10);
            }
            else{
                $("#mensajecvv").html("");
            }             
        }
        // no permite caracteres especiales
        
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
    // evito el uso de teclas que no sean numericas
    $("#numero").keypress(function(tecla){
        if(tecla.charCode < 48 || tecla.charCode > 57) return false;
        // no permite ceros
        //if(tecla.charCode == 48) return false;
    });

    // (function($){
    //     var maxFront = 0;
    //     var maxBack = 4;
    //     var lastLength = -1;
    //     $('.mask').on('keydown', function(){
    //       var self = this;
    //       setTimeout(function(){
    //          var val = $(self).val();
    //           var xxx = '';
    //           if(val.length > lastLength){
    //             $(self).data('value',  $(self).data('value') + val[val.length-1]);
    //           }else{
    //             var $value = $(self).data('value');
    //             $(self).data('value', $value.slice(0, $value.length-(lastLength-val.length)));
    //           }
      
    //           val = $(self).data('value');
    //           fr = val.slice(0,maxFront);
    //           bk = val.slice(-maxBack);
    //           if (val.length > maxFront+maxBack-1) {
    //             for (var i = maxFront; i < val.length-maxBack; i++) {
    //               xxx = xxx + '*';
    //             }
    //             $(self).val( fr + xxx + bk);
    //           }else{
    //             $(self).val(val)
    //           }
    //           lastLength = val.length;
    //           $('.data').text($(self).data('value'));
    //         });
    //     });
    // })(jQuery);
});