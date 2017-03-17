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
 			<div class="col-xs-12 col-sm-6 col-sm-offset-3">
 				<form class="form-horizontal" id="register_form"  >
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
					<label for="confrim_password" class="col-sm-2 control-label">確認密碼</label>
					<div class="col-sm-10">
					  <input type="password" class="form-control" id="confirm_password" placeholder="confrim_Password" required>
					</div>
				  </div>
				  <div class="form-group">
					<div class="col-sm-offset-2 col-sm-10">
					  <button type="submit" id="button" class="btn btn-default">確認註冊</button>
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
			$("#username").on("keyup",function(){
				if($(this).val()!='')
				{
					$.ajax({
			        type : "POST",	//表單傳送的方式 同 form 的 method 屬性
			        url : "php/check_username.php",  //目標給哪個檔案 同 form 的 action 屬性
			        data : {	//為要傳過去的資料，使用物件方式呈現，因為變數key值為英文的關係，所以用物件方式送。ex: {name : "輸入的名字", password : "輸入的密碼"}
			          'n' : $(this).val()	//代表要傳一個 n 變數值為，username 文字方塊裡的值
			        },
			        dataType : 'html' //設定該網頁回應的會是 html 格式
			      }).done(function(data) {
			        //成功的時候
			       // console.log(data); //透過 console 看回傳的結果
					if(data==1)
						{
							//console.log("data=1");
							//有使用帳號
							$("#username").parent().parent().removeClass('has-success').addClass('has-error');
							$("#button").attr('disabled',true);
						}
						else{
							//console.log("data=0");
							//無使用帳號
							$("#username").parent().parent().removeClass('has-error').addClass('has-success');
							$("#button").attr('disabled',false);
						}
			        
			        
			      }).fail(function(jqXHR, textStatus, errorThrown) {
			      	//失敗的時候
			      	alert("有錯誤產生，請看 console log");
			        console.log(jqXHR.responseText);
			      });
					
				}
				else
				{
					//不檢查帳號
					$("#username").parent().parent().removeClass('has-error').removeClass('has-success');
					$("#button").attr('disabled',false);
				}
			});
		//送出結果
			$("#register_form").on("submit",function(){
				//檢查兩組密碼是否相同
				if($("#password").val()!=$("#confirm_password").val())
				{
					$("#password").parent().parent().addClass('has-error');
					$("#confirm_password").parent().parent().addClass('has-error');
					alert("密碼錯誤");
					return false;
				}
				else{
					$.ajax({
			        type : "POST",	
			        url : "php/add_member.php",  
			        data : {	
			          'un' : $("#username").val(),
					  'pw' : $("#password").val()
			        },
			        dataType : 'html' 
			      }).done(function(data) {
			        //成功的時候
			        console.log(data); //透過 console 看回傳的結果
					if(data==1)
						{
							//console.log("data=1");
							//註冊成功 跳到登入頁
							window.location.href="admin/index.php";
						}
						else{
							//console.log("data=0");
							alert("註冊失敗 請洽管理員");
							return false;
							
						}
			        
			        
			      }).fail(function(jqXHR, textStatus, errorThrown) {
			      	//失敗的時候
			      	alert("有錯誤產生，請看 console log");
			        console.log(jqXHR.responseText);
			      });
					
				}
				return false;
			});
				   
	   });
		
	</script>
	
</body>
</html>


