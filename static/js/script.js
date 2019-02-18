// function UserAction(text) {
//     console.log('ya entro');
//     var xhttp = new XMLHttpRequest();
//     xhttp.onreadystatechange = function() {
//          if (this.readyState == 4 && this.status == 200) {
//              //alert(this.responseText);
//              console.log(this.responseText);
//          }
//     };
//     xhttp.open("POST", "https://qa.mitec.com.mx/ws3dsecure/Auth3dsecure", true);
//     xhttp.setRequestHeader("Content-type", "application/json");
//     xhttp.setRequestHeader('Access-Control-Allow-Origin', '*');
//     req = {'xml':text}
//     xhttp.send(req);
// }

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

    $("#numero").focusout(function() {
        var numero = $("#numero").val();
        if (numero.substring(0, 1) == 3){
            console.log(numero);
            $("#txtAmex").show();
        }
    });
});