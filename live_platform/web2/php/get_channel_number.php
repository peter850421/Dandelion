<?php
require_once 'redis_db.php';
require_once 'function.php';


if($_SESSION['redis'])
{

  //var_dump($redis->sMembers "123");
  echo $redis->SCARD("channel_id_{$_POST['id']}");
  



}
else{

  echo '無法連線redis : <br>';


}
//$check_number=channel_number('132','123');
//$check_number=channel_number($_POST['id'],$ip);
//echo $check_number;
 ?>
