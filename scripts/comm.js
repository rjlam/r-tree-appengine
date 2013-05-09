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

function returnRectangles(lst){
	console.log(lst)
	
	return false;	
}

function bulkLoadData(){
	console.log("loading data");
	$.ajax({
		async: false,
		global: false,
		url: '/bulk_load',
		type: 'POST',
		dataType: "text",
	  	success: function(data) {
			$("#status").dialog( "close" );
			$("#loadDiv").hide();
			return false;
		},
		error: function(data) {
			showStatus("Bulk loading failed: "+data);
			return false;
		}		
	});
	return false;
}

/*
 * Communication back and forth between server and client
 * */
// Send a query string to the server
function sendQuery(sPoint, ePoint){
	var sendData = {'client_id': client_id, 'startPoint': sPoint, 'endPoint': ePoint};
	$.ajax({
		async: false,
		global: false,
		url: '/send_query',
		data: sendData,
		type: 'POST',
		dataType: "text",
	  success: function(data) {
		$("#dataCanvas").remove();
		$("#canvas").append("<canvas id='dataCanvas' width='300' height='300'></canvas>");
		$("#messageDiv").empty();
		var json = JSON.parse(data);
		var lst = json.rect;
		var glst = json.grect;
		if (json.type == "error"){
			console.log("There was a problem with your query input: "+json.message);
			$("#messageDiv").append("There was a problem with your query input: "+json.message);
			$("#status").dialog( "close" );
			return false;
		}
		
		if (json.type == "results"){
			var sp = sPoint.split(",")
			var scaleFactor = 500;
			//sp[0] = scaleFactor*parseFloat(sp[0]) + parseFloat(json.minVals["mx"]);	
			sp[0] = scaleFactor*parseFloat(json.sp.x) + parseFloat(json.minVals["mx"]);	
			//sp[1] = (scaleFactor*-1.0*parseFloat(sp[1])) + parseFloat(json.minVals["my"]);	
			sp[1] = (scaleFactor*-1.0*parseFloat(json.sp.y)) + parseFloat(json.minVals["my"]);	
			var ep = ePoint.split(",");
			ep[0] = scaleFactor*parseFloat(json.ep.x) + parseFloat(json.minVals["mx"]);
			ep[1] = (scaleFactor*-1.0 * parseFloat(json.ep.y)) +  parseFloat(json.minVals["my"]);
						
			var canvas = document.getElementById('dataCanvas')
			var ctx = null;
			if (canvas.getContext){
				ctx = canvas.getContext('2d');
			} else {
				$("#messageDiv").append("Your browser does not support the canvas object. Cannot draw results.");
				return false;
			}
			ctx.beginPath();
			for (var i = 0; i < glst.length ; i++){
				r = glst[i].res
				ctx.rect(r[0],r[1],r[2],r[3]);		
			}
			ctx.stroke();
			
			if (lst.length > 1) {
				$("#messageDiv").append("Your query was submitted successfully. Your number of results: "+json.rect.length);
				ctx.beginPath();
				ctx.strokeStyle="#00FF00";
				for (var i = 0; i < lst.length ; i++){
					r = lst[i].res
					ctx.rect(r[0],r[1],r[2],r[3]);		
				}
				ctx.stroke();
			} else {
				$("#messageDiv").append("Your query was submitted successfully. No route can be found between your start and destination points.");
			}
			// mark start and end in red
			ctx.beginPath();
			ctx.fillStyle="#FF0000";
			ctx.moveTo(sp[0], sp[1]);
			ctx.arc(sp[0], sp[1],2,0,Math.PI*2,true);
			ctx.moveTo(ep[0], ep[1]);
			ctx.arc(ep[0], ep[1],2,0,Math.PI*2,true);
			ctx.fill();
			//ctx.fillRect(sp[0], sp[1], 2,2);		
			//ctx.fillRect(ep[0], ep[1], 2,2);
		} else {
			console.log('Missing message.type');
		}
		$("#status").dialog( "close" );
		return false;
	}
	,
	error: function(data) {
		alert("error..." + data) ;
	} 
	});
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
		console.log("Your query was submitted successfully. Your number of results: "+message.rect);
		$("#messageDiv").append("Your query was submitted successfully. Your number of results: "+message.rect);
		returnRectangles(message.rect)
		return;
	}
}
