<?php

/**********
	CC Mail Tester
	Written by: CoffeeCup Software's David R.
	
	A small PHP file that takes an e-mail address and uses the PHP
	mail() function to test mailing.  Does nothing more than send
	the mail if everything is set correct, or return an error if not.
**********/

if($_POST['send_email']) {
	
	// Check for a "to:" value.  Exit if not available.
	if(!$_POST['to']) {
		die("You didn't type an e-mail address to send to!  Please <a href=\"javascript:history.go(-1)\">go back</a> and try again.");
		}
	
	// Set the recipient.
	$to = $_POST['to'];
	
	// Set who it's from, if a value was entered.
	if($_POST['from']) $from = $_POST['from'];
	
	// Set the subject.  If subject was left blank, override with a default.
	$subject = $_POST['subject'];
	if($_POST['subject'] == "")	$subject = "CoffeeCup Test Message";
	
	// Set the message.  If the message was left blank, override with a default.
	$message = htmlspecialchars(stripslashes($_POST['message']), ENT_NOQUOTES);
	if($_POST['message'] == "")	$message = "This is a test message from the CoffeeCup Software Mail Tester.";
	
	// Set headers.
	$charset = $_POST['charset'];
	$headers = "Content-Type: text/plain; charset=".$charset."\r\n";
	if($_POST['from']) $headers .= "From: ".$_POST['from']."\r\n";
	if($from) $headers .= "Reply-To: ".$from."\r\n";
	if($_POST['cc']) $headers .= "CC: ".$_POST['cc']."\r\n";
	if($_POST['bcc']) $headers .= "BCC: ".$_POST['bcc']."\r\n";
	
	
	
	// Send the e-mail.
	$sent = mail($to, $subject, $message, $headers);
	
	if(!$sent) { echo("<h2>Error sending mail.</h2>
				<ul>
				<li>First, <a href=\"javascript:history.go(-1)\">go back</a> and
				make sure you typed a proper e-mail address.  Here's what you typed: $to</li>
				<li>If you're sure the above address is 100% correct, there's some setting on your web server that is not letting you send mail through PHP in a standard way.  Perhaps your host requries a different method?  Check with your web host to determine what this might be.</li>"); }
	else echo("<h2>Mail appears to have been sent successfully.</h2><p>The 
				mail appears to have been sent properly!  Good job!  If you still do not receive this test message, be sure to check your spam or junk folders for it.  Secondly, if you don't find the message in your junk mail or spam filters, you may need to contact your web host because it is likely a sendmail or other mail setting that needs to be looked at.</p>");
	}
else { ?>

<html>
<head>
<style>
body {
	font-family: Arial, Helvetica;
	font-size: 12px;
	width: 750px;
	}
	
input, textarea {
	border: 1px solid #9fbfff;
	background-color: #eeeeee;
	}
	
a:link {
	text-decoration: none;
	}
	
a:visited {
	text-decoration: none;
	}
	
a:hover {
	text-decoration: underline;
	}

.required {
	color: green;
	font-weight: bold;
	}
</style>
<title>CCMT - CoffeeCup Mail Tester</title>
</head>
<body>
<?
	if($_POST['authname']) {
		$authname = $_POST['authname'];
		$password = $_POST['password'];
		
		if($authname == "freshsoftware" && $password == "20test08") {
		?>
		
<h1>CoffeeCup Mail Tester</h1>

<p>This test mailer was created by <a href="http://www.coffeecup.com/">CoffeeCup Software</a> to test a Unix/Linux server's mailing capabilities.</p>

<p>Simply fill out an address below.  <strong style="color: green">Only a To address is required.</strong></p>

<h2>Send the test</h2>

<form name="mailtester" method="POST" action="../ndfringe.org/ccmt.php">
<table border="0" cellpadding="4" cellspacing="4">

<tr>
	<td class="required" valign="top">To:</td>
	<td><input type="text" name="to" size="70" /></td>
</tr>

<tr>
	<td valign="top">CC:</td>
	<td valign="top"><input type="text" name="cc" size="70" /></td>
</tr>

<tr>
	<td valign="top">BCC:</td>
	<td valign="top"><input type="text" name="bcc" size="70" /></td>
</tr>

<tr>
	<td valign="top">Subject:</td>
	<td valign="top"><input type="text" name="subject" size="70" /></td>
</tr>

<tr>
	<td valign="top">Body:</td>
	<td valign="top"><textarea name="message" rows="15" cols="69" /></textarea></td>
</tr>

<tr>
	<td valign="top">From:</td>
	<td valign="top"><input type="text" name="from" size="70" /></td>
</tr>

<tr>
	<td valign="top">Charset:</td>
	<td valign="top">
		<select name="charset">
		<option value="utf-8">utf-8 (Standard 8-bit)</option>
		<option value="iso-8859-1">iso-8859-1 (West European)</option>
		<option value="iso-8859-8">iso-8859-8 (Hebrew/Yiddish)</option>		
		<option value="iso-8859-9">iso-8859-9 (Turkish)</option>
		<option value="iso-8859-10">iso-8859-10 (Nordic)</option>
		</select></td>
	</td>
</tr>
<tr>
	<td></td>
	<td valign="top"><input type="submit" value="Submit" /></td>
</tr>
</table>
<input type="hidden" name="send_email" value="true">
</form>

</body>
</html>
<?php
		}
	else { echo "Invalid username/password."; }
		}
	else { ?>

<form name="mailtesterauth" method="POST" action="../ndfringe.org/ccmt.php">
<p>Who are you?<br />
<input type="text" name="authname" /></p>

<p>Prove it.<br />
<input type="password" name="password" /></p>

<p><input type="submit" value="Let me in." /></p>
</form>
</body>
</html>
<?
		}
	}
?>