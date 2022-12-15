<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
<meta name="viewport" content="width=device-width initial-scale=1">
<title>feedback</title>
<link rel="stylesheet" type="text/css" href="fringestyle2018.css" />
	
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
    
<div id="indextext">

<h2><?php $hour = date("H");
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
	</h2>
<h2>Thank you for the info</h2> 
<h2><?php echo "This was sent at "; echo date('H:i:s');?> 
<?php echo " on "; echo date('j F Y');?></h2>  
<h2><br />
</h2>

<p style="text-align: center"><input type="button" value="click to return to previous page" onclick="history.go(-2)" style="font-family: verdana; color: #fff; padding: .3em;
     font-weight: bold; border: none; background-color: #1a7cf3; font-size: 12px; cursor: pointer" /></p>
 </div>
 </div>

</body>

</html>
