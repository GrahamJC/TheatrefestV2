<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<meta http-equiv="Content-Type" content="text/html; charset=windows-1252" />
<title>feedback</title>
<link rel="stylesheet" type="text/css" href="../ndfringe.org/fringestyle2.css" />
</head>

<body>
<div id="holder">
<div id="fringelogo">
        <img border="0" src="../ndfringe.org/bulletinlogo.gif" alt="fringe logo - click for home page" />       
        </div>
<div id="ndflogo08">
	<img src="../ndfringe.org/ndflogo08.gif" alt="North Devon Festival logo - click for website" border="0" usemap="#Map2"
     />
<map name="Map2" id="Map2"><area shape="rect" coords="5,5,174,97" href="http://www.northdevonfestival.org/northdevonfestival/festival.asp" /></map></div>
    
<div style="position: absolute; left: 235px; top: 200px; text-align: center; width: 40%">

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
<h2>Thank you for your comments.</h2> 
<h2><?php echo "These were sent at "; echo date('H:i:s');?> 
<?php echo " on "; echo date('j F Y');?></h2>  
<h2>They will be read and acted upon as soon as possible.</h2>

<br /><br />
<p style="text-align: center"><input type="button" value="click to return to previous page" onclick="history.go(-2)" style="font-family: Arial; color: #dddddd; 
     font-weight: bold; border-style: bevel; top-border: 2px #cccccc; right-border: 2px #cccccc; bottom-border: 2px #333333;
     left-border: 2px #cccccc; background-color: #4033cc; font-size: 12px; cursor: pointer" /></p>
 </div>
 </div>
 <div id="bgd">
<img src="../ndfringe.org/bgd.jpg"></div>

</body>

</html>
