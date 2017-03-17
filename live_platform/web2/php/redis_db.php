<?php
//session
@session_start();

$redis = new Redis();
$_SESSION['redis']=$redis->connect('127.0.0.1', 6379);

if($_SESSION['redis'])
{


	//echo "Server is running: " . $redis->ping();

}
else{

	echo '無法連線redis : <br>';


}


?>
