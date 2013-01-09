/*  TODO: onSelect for date pickers.    */
$.urlParam = function(name){
    var results = new RegExp('[\\?&]' + name + '=([^&#]*)').exec(window.location.href);
    return results[1] || 0;
}

$(function()
{
   $('#alert_type').change(function(evt)
    {	
        if ($(this).attr('value') != ''){window.location = (window.location.pathname + '?type=' +
        $(this).attr('value'));
	} else {
			window.location = window.location.pathname;			
			}
    });

    condDisableValues();
    $('#alert_value').change(function()
    {
        if ($(this).attr('value') != ''){ window.location = (window.location.pathname + '?value=' +
        $(this).attr('value') + '&type=' + $('#alert_type').attr('value'));
	}
		else {
			window.location = window.location.pathname;			
			}
    });

    
});

function condDisableValues()
{
    var loc = window.location.toString();
    if(loc.search(/type/) != -1 && $.urlParam('type') !="") {

		if($.urlParam('type') !="REMINDER") $("label[for=rem_value],#rem_value").hide();
		return;
		}
    $("label[for=alert_value],#alert_value").hide();
    
    $("label[for=rem_value],#rem_value").hide();


}


// javascript for the rheahttpclient
url = "/api/client";

$(document).ready(function(){
	$('#alert_form').submit(function(){ sendMsg(); return false; });
	//setInterval("checkMsgs()", 5000);
});

function sendMsg() {
	if ($('#alert_value').val().length > 0 && $('#patid').val().length ==16 && $('#locid').val().length > 0 && $('#village').val().length > 0 ) {
		req = url + "/" + escape($('#patid').val())+ "?al="+escape($('#alert_value').val()) + "&type="+escape($('#alert_type').val()) + "&loc=" + escape($('#locid').val()) + "&vill=" + escape($('#village').val() ) + "&value=" + escape($('#rem_value').val() );

		$.getJSON(
			req,
			function (response) { if (response) {
				snippet = '<tr class="in"><td class="phone">' + response + '</td><td class="dir">&laquo;</td><td class="msg">' + response + '</td><td class="info">' + response + ' characters</td></tr>';
				$('#log').append(snippet);
				fixClasses();
				$('div.tester').scrollTo('#log tr:last', 800);
				
			}}
		);
	}
}

function fixClasses(){
	$('#log tr').removeClass('first');
	$('#log tr').removeClass('last');
	$('#log tr:first').addClass('first');
	$('#log tr:last').addClass('last');
}

function decode(str) {
	str = str.replace(/%23/gi, "#");
	str = str.replace(/%24/gi, "$");
	str = str.replace(/%26/gi, "&");
	str = str.replace(/%3D/gi, "=");
	str = str.replace(/%3B/gi, ";");
	str = str.replace(/%2C/gi, ",");
	str = str.replace(/%3A/gi, ":");
	str = str.replace(/%3F/gi, "?");
	str = decodeURI(str);
	return str;
}

function checkMsgs() {
	if ($('#phone').val().length > 0) {
		req = "http/proxy/" + $('#phone').val() + "/json_resp";
		$.getJSON(
			req,
			function (response) { if (response) {
				snippet = '<tr class="out"><td class="phone">' + response.phone + '</td><td class="dir">&raquo;</td><td class="msg">' + decode(response.message) + '</td><td class="info">' + decode(response.message).length + ' characters</td></tr>';
				$('#log').append(snippet);
				fixClasses();
				$('div.tester').scrollTo('#log tr:last', 800);
			}}

		);
	}
}
