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

function showStatus(msg){
	$( "#status" ).html("Please stand by while your query is being processed...");
	if (msg != null)
		$( "#status" ).html(msg);
	$( "#status" ).dialog({
	                        width:450,
	                        modal: true,
	                });
	return false;
}

function submitQuery1(){
	$("#startPoint").val("-122.1,37.7");
	$("#endPoint").val("-122.2,37.8");
	$("#query_box_form").submit();
	return false;
}

function submitQuery2(){
	$("#startPoint").val("-122.259,37.8368");
	$("#endPoint").val("-122.258,37.8344");
	$("#query_box_form").submit();
	return false;
}

function submitQuery3(){
	$("#startPoint").val("-151,10");
	$("#endPoint").val("-101,66");
	$("#query_box_form").submit();
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