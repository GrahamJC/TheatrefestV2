<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<meta http-equiv="Content-Type" content="text/html; charset=windows-1252" />
<meta name="viewport" content="width=device-width initial-scale=1">
<title>feedback response</title>
<link rel="stylesheet" type="text/css" href="fringestyle2018.css" />
	
	<style>#guidelines {position: absolute; left: 7%; top: 133em; width: 86%}
@media (min-width: 610px) and (max-width: 910px) {#guidelines {top: 17.5em; left: 69%; width: 29% }} 
@media (min-width: 910px) {#guidelines {top: 23em; left: 72%; width: 26%}}</style>

	<script>
function myFunction() {
    document.getElementById("myDropdown").classList.toggle("show");
}

// Close the dropdown if the user clicks outside of it
window.onclick = function(event) {
  if (!event.target.matches('.dropbtn')) {

    var dropdowns = document.getElementsByClassName("dropdown-content");
    var i;
    for (i = 0; i < dropdowns.length; i++) {
      var openDropdown = dropdowns[i];
      if (openDropdown.classList.contains('show')) {
        openDropdown.classList.remove('show');
      }
    }
  }
}
</script>
</head>

<body>

<div id="holder">
 
<div id="bridge">
	<a href="index.htm"><img src="18/bridgeArtReady.png" alt=""  /></a>
  </div>
	
 <div id="bridge2">
	 <a href="index.htm"><img src="18/bridgeArtReady.png" alt="" /></a>
  </div>
	
<div id="bridge3">
	<a href="index.htm"><img src="18/bridgeArtReady.png" alt="" /></a>
  </div>  
  
  <div id="bridgemobile">
<a href="index.htm"><img src="18/bridgeArtReadymobile.png" alt="" />
	  </a>
</div>

<div id="menubar"></div>

 <div id="topmenu">
<ul id="menu2">
  		<li><a href="index.htm">home</a></li>
  	     <li><a href="http://tickets.theatrefest.co.uk/program/show">shows</a></li>
   	   
	<li><a href="http://tickets.theatrefest.co.uk/program/schedule">times</a></li>
	
	<li><a href="http://tickets.theatrefest.co.uk/program/venue">venues</a></li>
	
	<li><a href="18/booking.htm">tickets</a></li>
	
        <li><a href="performers.htm">performers</a></li>
        <li><a href="volunteers.htm">volunteer</a></li>
	<li><a href="contact.htm">contact</a></li>
   	    <li><a href="">&nbsp; &nbsp; &nbsp;</a></li> 
	<li><a href="">&nbsp;</a></li>  
	
	<li><a href="http://tickets.theatrefest.co.uk/tickets/myaccount">my account</a></li> 
    </ul>
  </div>

 <div id="topminimenu">
   <div class="dropdown">
<button onclick="myFunction()" class="dropbtn"></button>
  <div id="myDropdown" class="dropdown-content">
   <ul>
  		<li><a href="index.htm">home</a>
			<a href="http://tickets.theatrefest.co.uk/program/show">shows</a></li>
   	   
	  <li><a href="http://tickets.theatrefest.co.uk/program/schedule">times</a></li>
	
	   <li><a href="http://tickets.theatrefest.co.uk/program/venue">venues</a></li>
	
	   <li><a href="18/booking.htm">tickets</a></li>
	
	   <li> <a href="performers.htm">performers</a></li>
	   <li> <a href="volunteers.htm">volunteer</a></li>
	   <li> <a href="contact.htm">contact</a></li>
	   <li><a href="">&nbsp;</a></li>  
	<li><a href="http://tickets.theatrefest.co.uk/tickets/myaccount">my account</a></li>
	  </ul>
    
  </div>
</div>
	</div>

<div id="response">

<p><?php $hour = date("H");
	if ($hour < 12) {
	echo "Good morning ";
	}
	elseif ($hour < 17) {
	echo "Good afternoon ";
	}
	else {
	echo "Good evening ";
	}
	?>
	</p>
<p><b>Thank you for your comments.</b></p> 
<p><?php echo "These were sent at "; echo date('H:i:s');?> 
<?php echo " on "; echo date('j F Y');?></p>  
<p>They will be read and acted upon as soon as possible.</p>

<br /><br />

 </div>
 </div>

</body>

</html>