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

function showStatus(){
	$( "#status" ).html("Please stand by while your query is being processed...");
	$( "#status" ).dialog({
	                        width:450,
	                        modal: true,
	                });
	return false;
}

// Handles the input from the user and prepare it for message to server
function parseQuery(){
	$( "#confirm" ).html("Your start and end point need to be of the form 'xy.z,ab.c'. Is that the case?");
	$( "#confirm" ).dialog({
	                        width:450,
	                        modal: true,
	                        buttons: {	                                
	                                Yes: function() {
											$("#messageDiv").empty();
											$(this).dialog( "close" );
											showStatus();
											var queryRun = function(){
	 											var sPoint = $('#startPoint').val();
												var ePoint = $('#endPoint').val();
												sendQuery(sPoint, ePoint);
												return false;
											};
											// Javascript is special, that's why I need
											// a 2 second timeout to make all the dialogs
											// appear in correct order.
											setTimeout(queryRun, 2000);
											return false;
	                                },
									No: function() {
										$("#status").dialog( "close" );
										$(this).dialog( "close" );
										return false;
									}
	                        }
	                });
}

function setMsg(){
	$("#messageDiv").empty();
	$("#messageDiv").append("Now bulk loading RTree. This may take a while. Do not reload or interrupt this page.");
	return false;
}

$(document).ready(init);