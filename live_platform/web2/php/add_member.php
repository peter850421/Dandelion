<?php
require_once 'live_stream_db.php';
require_once 'function.php';
$check_member = add_member($_POST['un'],$_POST['pw']);
$user_id = check_user_id($_POST['un']);
$check_channel = add_channel($_POST['un'],$user_id['id'],$_POST['pw']);


if($check_member && $check_channel)
{
	echo '1';
	
}
else
{
	echo "0";
}

?>