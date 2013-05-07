/*
 * General client end functions! Aaron, edit this file.
 */
var initialized = false;

function init(){
	if (!initialized){
		createChannel();
	}
	initialized = true;
}

// Handles the input from the user and prepare it for message to server
function parseQuery(){
	var c = confirm("Your start and end point need to be of the form 'xy.z,ab.c'. Is that the case?");
	if (!c)
		return false;
	var sPoint = $('#startPoint').val();
	var ePoint = $('#endPoint').val();
	return sendQuery(sPoint, ePoint);	
}



$(document).ready(init);