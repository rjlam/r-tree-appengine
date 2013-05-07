/*
 * File for communication between server and client
 */

/*
 * Channel Functions
 * */
function createChannel() {
	channel = new goog.appengine.Channel(server_token);
    socket = channel.open();
    socket.onopen = channelOnOpen;
    socket.onmessage = channelOnMessage;
    socket.onerror = channelOnError;
    socket.onclose = channelOnClose;
}

channelOnOpen = function() {
	console.log('channel opened');
}

channelOnMessage = function(message) {
	console.log('channelOnMessage');
	
	handleServerMessage(message);	
}

channelOnError = function(error) {
	console.log('channel error: ' + error.description + '(' + error.code + ')');
}

channelOnClose = function() {
	console.log('channel closed');
}

/*
Updates channel when user is host
*/
function updateChannel(play, endflag, num) {
	console.log('updateChannel: ' + server_session_key + ', ' + hostingIndex + ', ' + play + ', ' + endflag + ', ' + num);

	$.post('/get',
		{'session_key': server_session_key, 'curIdx': hostingIndex, 'play': play, 'endflag': endflag, 'num': num},
		function(message) {
			console.log('/update response:' + message);
		}
	);
}


/*
 * Communication back and forth between server and client
 * */
// Send a query string to the server
function sendQuery(sPoint, ePoint){
	$.post('/send_query', {'client_id': client_id, 'startPoint': sPoint, 'endPoint': ePoint});
	return true;
}


// Parse the message from the server
function handleServerMessage(message){
	message = message.data;

	while (typeof message == 'string' && message.length > 0) {
		message = JSON.parse(message);		
	}
	
	if (message.type == 'undefined') {
		console.log('Missing message.type');
		return;
	}
	
	if (message.type == 'error'){
		console.log("There was a problem with your query input: "+message.message);
		$("#messageDiv").append("There was a problem with your query input: "+message.message);
		return;
	}
	
	if (message.type == 'results') {
		console.log("Your query was submitted successfully. Your list of rectangles: "+message.rect);
		$("#messageDiv").append("Your query was submitted successfully. Your list of rectangles: "+message.rect);
		//returnRectangles(message.rect)
		return;
	}
}