<?php 
require_once'../php/live_stream_db.php';
require_once'../php/function.php';
 
if(!isset($_SESSION['is_login']) || !$_SESSION['is_login'] )
{
	header("Location:login.php");
}
//if($_GET['i']!=$_SESSION['login_user_id'])
//{
	//header("Location:login.php");
	
//}

$data= get_user_channel($_GET['i']);
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
					  <li role="presentation"><a href="../index.php">前台首頁</a></li>
					   <li role="presentation" class="active"><a href="index.php">後台首頁</a></li>
					  <li role="presentation"><a href="../tutor.php">教學</a></li>
					  <li role="presentation"><a href="logout.php">登出</a></li>
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
 				<form id=update_channel_form  method="post">
				  <div class="form-group">
					<label for="info">更改頻道資訊</label>
					  
				  </div>
				  <div class="form-group">
				  	<textarea id=info class="form-control" rows=10 ><?php echo $data['info'] ;?></textarea>
				  	
				  	
				  </div>
				<!--  <div class="form-group">
					<label for="publish">是否發布</label>
					<select id="publish" class="form-control">
						<option value="1" <?php //echo($data['publish']=='1')?'selected':'';?>>發布</option>
						<option value="0" <?php //echo($data['publish']=='0')?'selected':'';?>>不發布</option>
						
					</select>
				  </div>-->
				  <button type="submit" class="btn btn-success">儲存更改</button>
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
		
			
		//送出結果
			$("#update_channel_form").on("submit",function(){
					$.ajax({
			        type : "POST",	
			        url : "update_channel.php",  
			        data : {	
			          'info' : $("#info").val(),
					  //'pub' : $("#publish").val()
					  
			        },
			        dataType : 'html' 
			      }).done(function(data) {
			        //成功的時候
			        console.log(data); //透過 console 看回傳的結果
					if(data ==1)
						{
							alert("成功");
							console.log(data);
							window.location.href="index.php";
						}
						else
						{
							console.log(data);
							alert("失敗");
							
							
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


