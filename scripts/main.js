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
function parseQuery(element){
	var query = element.getElementsByTagName('input');
	sendQuery(query);
}


$(document).ready(init);