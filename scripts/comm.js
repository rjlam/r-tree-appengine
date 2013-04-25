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

	$.post('/update',
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
function sendQuery(qString){
	$.post('/send_query', {'client_id': client_id, 'query:' qString});
}

// Parse the message from the server
function handleServerMessage(message){
	message = message.data;

	while (typeof message == 'string' && message.length > 0) {
		message = JSON.parse(message);
	}
	if (typeof message.type == 'undefined') {
		console.log('Missing message.type');
		return;
	}
	
	if (typeof message.type == 'results')
}