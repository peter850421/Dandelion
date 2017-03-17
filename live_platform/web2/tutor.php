<?php 
require_once'php/live_stream_db.php';
require_once'php/function.php';

?>
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
 <!-- 給行動裝置或平板顯示用，根據裝置寬度而定，初始放大比例 1 -->
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live_Stream</title>
<!-- CSS -->
<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
<link rel="stylesheet" href="css/style.css">
</head>



<body>
<div class="top">
<div class="jumbotron">
		<div class="container">
			<div class="row">
				<div class="col-xs-12">
					<h1 class="text-center">Stream-Live</h1> 


					<ul class="nav nav-pills">
					  <li role="presentation"><a href="index.php">首頁</a></li>
					  <li role="presentation"><a href="tutor.php">教學</a></li>
					  <li role="presentation"><a href="register.php">註冊</a></li>
					  <li role="presentation"><a href="admin/login.php">登入</a></li>
					</ul>
				</div>
			</div>
		</div>
	</div>
</div>

<div class="main">
 	<div class="container">
 		<div class="row">
 			<div class="col-xs-12">
 				<h3>直播設定教學</h3>
 				<div class="col-xs-4">
 					<p class="lead">1.註冊並登入 </p>
 				</div>
 				<div class="col-xs-8">
 					<img src="img/web_key.jpg" alt="key" class="img-thumbnail" class="img-responsive" class="tutor" >
 				</div>
			</div>
		</div>
		<div class="row">
 			<div class="col-xs-12">		
 				<div class="col-xs-4">
 					<p class="lead">2.進行obs設定</p>
 				</div>
 				<div class="col-xs-8">
 					<img src="img/obs_setteing.jpg" alt="key" class="img-thumbnail" class="img-responsive" class="tutor">
 				</div>
 			</div>
		</div>		
		<div class="row">
 			<div class="col-xs-12">				
 				<div class="col-xs-4">
 					<p class="lead">3.直播串流伺服器設定</p>
 					<ul >
					  <li>選擇自訂串流伺服器</li>
					  <li>將系統給的串流金鑰填入</li>
					</ul>
				</div>
 				<div class="col-xs-8">
 					<img src="img/obs_stream.jpg" alt="key" class="img-thumbnail" class="img-responsive" class="tutor">
 				</div>
			</div>
		</div>
		<div class="row">
 			<div class="col-xs-12">		
 				<div class="col-xs-4">
 					<p class="lead">4.直播輸出設定</p>
 					<ul >
					  <li>選擇進階輸出模式</li>
					  <li>編碼器x264</li>
					  <li>位元率2400至2500</li>
					  <li>關鍵影格設定"2秒"</li>
					</ul>
				</div>
 				<div class="col-xs-8">
 					<img src="img/obs_keyframe.jpg" alt="key" class="img-thumbnail" class="img-responsive" class="tutor" >
 				</div>			
 			</div>
		</div>
 		<div class="row">
 			<div class="col-xs-12">		
 				<div class="col-xs-4">
 					<p class="lead">5.開始直播</p>
 				</div>
 				<div class="col-xs-8">
 					<img src="img/obs_start.jpg" alt="key" class="img-thumbnail" class="img-responsive" class="tutor">
 				</div>
 			</div>			
 		</div>		
 	</div>
 		
</div>

<div class="foot">
 <div class="container">
        <!-- 建立第一個 row 空間，裡面準備放格線系統 -->
        <div class="row">
          <!-- 在 xs 尺寸，佔12格，可參考 http://getbootstrap.com/css/#grid 說明-->
          <div class="col-xs-12">
            <p class="text-center">
              &copy; <?php echo date("Y")?>
              Stream-Live
            </p>
          </div>
        </div>
	</div>
</div>
</body>
</html>


