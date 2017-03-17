<?php
require_once 'redis_db.php';
require_once 'function.php';
/*Get IP*/
if (!empty($_SERVER['HTTP_CLIENT_IP']))
{
  $ip=$_SERVER['HTTP_CLIENT_IP'];
}
else if (!empty($_SERVER['HTTP_X_FORWARDED_FOR']))
{
  $ip=$_SERVER['HTTP_X_FORWARDED_FOR'];
}
else
{
  $ip=$_SERVER['REMOTE_ADDR'];
}

if($_SESSION['redis'])
{
  $redis->SADD($_POST['id'],"{$ip}");
  //set 3 sec expiring
  $redis->setTimeout($_POST['id'],3);

  //var_dump($redis->sMembers "123");
  echo ($redis->SCARD($_POST['id']));



}
else{

  echo '無法連線redis : <br>';


}
//$check_number=channel_number('132','123');
//$check_number=channel_number($_POST['id'],$ip);
//echo $check_number;
 ?>
