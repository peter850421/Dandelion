<?php
@session_start();

function get_channel_list()
{
	$datas=array();
	$sql = "SELECT * FROM `channel` WHERE `publish` = 1";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		while($row =mysqli_fetch_assoc($querry))
		{
			$datas[]= $row;
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $datas;
}


function get_channel($id)
{
	$result = null;
	$sql = "SELECT * FROM `channel` WHERE `publish` = 1 AND `id`= {$id} ;";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_num_rows($querry)==1)
		{
			$result = mysqli_fetch_assoc($querry);
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function check_username($username)
{
	$result = null;
	$sql = "SELECT * FROM `user` WHERE `username` ='{$username}'";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_num_rows($querry)==1)
		{
			$result = true;
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function add_member($username,$password)
{
	$result = null;
	$password=md5($password);
	$create_date = date('Y-m-d H:i:s');
	$sql = "INSERT INTO `user` (`username`,`password`,`create_date`) VALUES ('{$username}','{$password}','{$create_date}')";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_affected_rows($_SESSION['link'])>=1)
		{
			$result = true;
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function add_channel($username,$user_id,$publish_key)
{
	$result = null;
	$publish_key=sha1($publish_key);
	$sql = "INSERT INTO `channel` (`username`,`publish`,`user_id`,`publish_key`) VALUES ('{$username}','0','$user_id','$publish_key')";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_affected_rows($_SESSION['link'])>=1)
		{
			$result = true;
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function check_user_id($username)
{
	$result = null;
	$sql = "SELECT * FROM `user` WHERE `username` = '{$username}'  ;";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_num_rows($querry)==1)
		{
			$result = mysqli_fetch_assoc($querry);
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function verify_user($username,$password)
{
	$result = null;
	$password=md5($password);
	$sql = "SELECT * FROM `user` WHERE `username` ='{$username}' AND `password`='{$password}' ;";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_num_rows($querry)>=1)
		{
			$user=mysqli_fetch_assoc($querry);
			$_SESSION['is_login']= true;
			$_SESSION['login_user_id']= $user['id'];
			$result = true;
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}
	//print_r("sqlget_{$result}");
	return $result;


}

function get_user_channel($user_id)
{
	$result = null;
	$sql = "SELECT * FROM `channel` WHERE `user_id`= {$user_id} ;";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_num_rows($querry)==1)
		{
			$result = mysqli_fetch_assoc($querry);
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function update_channel($info,$user_id)
{
	$result = null;
	$sql = "UPDATE `channel` SET `info`='{$info}' WHERE `user_id`='{$user_id}'; ";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_affected_rows($_SESSION['link'])==1)
		{
			$result = true;


		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function rtmp_verify_user($n,$publish_key)
{
	$result = null;

	$sql = "SELECT * FROM `channel` WHERE `username` ='{$n}' AND `publish_key`='{$publish_key}' ;";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_num_rows($querry)>=1)
		{
			$user=mysqli_fetch_assoc($querry);
			$_SESSION['is_login']= true;
			$_SESSION['login_user_id']= $user['id'];
			$sql1 = "UPDATE `channel` SET `publish`='1' WHERE `username` ='{$n}'; ";

			$result = true;
		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}
	//print_r("sqlget_{$result}");
	return $result;


}
function update_channel_publish($n)
{
	$result = null;
	$sql = "UPDATE `channel` SET `publish`='1'  WHERE `username`='{$n}' ; ";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_affected_rows($_SESSION['link'])==1)
		{
			$result = true;


		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}

function rtmp_done($username)
{
	$result = null;
	$sql = "UPDATE `channel` SET `publish`='0' WHERE `username`='{$username}'; ";
	$querry = mysqli_query($_SESSION['link'],$sql);

	if($querry)
	{
		//success
		if(mysqli_affected_rows($_SESSION['link'])==1)
		{
			$result = true;


		}
	}
	else
	{
		echo "{$sql}語法請求失敗:<br/>" . mysqli_error($_SESSION['link']);
	}

	return $result;


}
?>
