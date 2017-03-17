<?php
require_once '../php/live_stream_db.php';
require_once '../php/function.php';
$check = update_channel($_POST['info'],$_SESSION['login_user_id']);


if($check)
{
	echo '1';

}
else
{
	echo "0";
}

?>
