<?php 
// www.server.com/auth.php?user=felix&pass=felixpassword
require_once 'php/live_stream_db.php';
require_once 'php/function.php';
//check if querystrings exist or not
if(empty($_GET['n']))
   {
    //no querystrings or wrong syntax
    echo "wrong query input";
    header('HTTP/1.1 404 Not Found');
    exit(1);
   }

else
   {
	//querystring exist
		$check = rtmp_done($_GET['n']);
	//print_r("get_{$check}");
	if($check)
	{
		//header('HTTP/1.1 200'); 

	}
	else
	{
		echo "password or username wrong! ";
		header('HTTP/1.1 404 Not Found'); 
	}

   }




?>