<?php
require_once '../php/live_stream_db.php';
require_once '../php/function.php';
$check = verify_user($_POST['un'],$_POST['pw']);
//print_r("get_{$check}");
if($check)
{
	echo '1';
	
}
else
{
	echo "0";
}

?>