<?php
//session
@session_start();
$host = 'localhost';
$dbuser = 'root';
$dbpw = 'elnj4j;3xj4';
$dbname = 'live_stream_db';

$_SESSION['link']=mysqli_connect($host,$dbuser,$dbpw,$dbname);

if($_SESSION['link'])
{

	mysqli_query($_SESSION['link'],"SET NAMES utf8");
	//echo "success";

}
else{

	echo '無法連線mysql : <br>' . mysql_connect_error();


}

?>
