<?php 
require_once'../php/live_stream_db.php';
require_once'../php/function.php';
if(isset($_SESSION['is_login']) && $_SESSION['is_login'] )
{
	header("Location:index.php");
}
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
<link rel="stylesheet" href="../css/style.css">
</head>



<body>
<div class="top">
<div class="jumbotron">
		<div class="container">
			<div class="row">
				<div class="col-xs-12">
					<h1 class="text-center">Stream-Live</h1> 


					<ul class="nav nav-pills">
					  <li role="presentation"><a href="../index.php">首頁</a></li>
					  <li role="presentation"><a href="../tutor.php">教學</a></li>
					  <li role="presentation"><a href="../register.php">註冊</a></li>
					  <li role="presentation"><a href="login.php">登入</a></li>
					</ul>
				</div>
			</div>
		</div>
	</div>
</div>

<div class="main">
 	<div class="container">
 		<div class="row">
 			<div class="col-xs-12 col-sm-6 col-sm-offset-3">
 			<h1>會員登入</h1>
 				<form class="form-horizontal" id="login_form" method="post" >
				  <div class="form-group">
					<label for="username" class="col-sm-2 control-label">帳號</label>
					<div class="col-sm-10">
					  <input type="text" class="form-control" name="username" id="username" placeholder="username" required>
					</div>
				  </div>
				  <div class="form-group">
					<label for="password" class="col-sm-2 control-label">密碼</label>
					<div class="col-sm-10">
					  <input type="password" class="form-control" name="password" id="password" placeholder="Password" required>
					</div>
				  </div>
				  
				  <div class="form-group">
					<div class="col-sm-offset-2 col-sm-10">
					  <button type="submit" id="button" class="btn btn-default">登入</button>
					</div>
				  </div>
				</form>
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
	<script src="http://code.jquery.com/jquery-latest.min.js"></script>
	<script>
		//檢查輸入帳號密碼	
		$(document).on("ready",function(){
		//檢查帳號是否註冊
			
		//送出結果
			$("#login_form").on("submit",function(){
				
					$.ajax({
			        type : "POST",	
			        url : "very_user.php",  
			        data : {	
			          'un' : $("#username").val(),
					  'pw' : $("#password").val()
			        },
			        dataType : 'html' 
			      }).done(function(data) {
			        //成功的時候
			        //console.log(data); //透過 console 看回傳的結果
					if(data==1)
						{
							//console.log("data=1");
							//註冊成功 跳到登入頁
							window.location.href="index.php";
						}
						else{
							//console.log("data=0");
							alert("登入失敗");
							return false;
							
						}
			        
			        
			      }).fail(function(jqXHR, textStatus, errorThrown) {
			      	//失敗的時候
			      	alert("有錯誤產生，請看 console log");
			        console.log(jqXHR.responseText);
			      });
					return false;
			});
	   });
		
	</script>
	
</body>
</html>


