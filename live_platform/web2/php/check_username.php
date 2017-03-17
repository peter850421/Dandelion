<?php
require_once 'live_stream_db.php';
require_once 'function.php';
$check = check_username($_POST['n']);

if($check)
{
	echo '1';
	
}
else
{
	echo "0";
}

?>