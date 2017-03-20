<?php
require_once'php/live_stream_db.php';
require_once'php/function.php';
$datas = get_channel_list();
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
					  <li role="presentation" class="active"><a href="index.php">首頁</a></li>
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

 		<?php if(!empty($datas)):?>
 			<?php foreach($datas as $a_name):?>
 				<div class="col-xs-12 col-sm-4" >
 					<div class="thumbnail">
					  <img src="<?php echo '../hls/'."{$a_name['username']}".'_src.png'?>"  >
					  <div class="caption">
						<h3><?php echo "{$a_name['username']}"?></h3>
						<p class="channel_info"><?php echo mb_substr($a_name['info'],0,35,"UTF-8"); ?></p>
						<p class="text-nowrap">
						<a href="channel_server.php?i=<?php echo $a_name['id'];?>" class="btn btn-success" role="button">Server</a>
						<a href="../hls/output/<?php echo "{$a_name['username']}"?>.m3u8" class="btn btn-success" role="button">Server-IOS</a>
						<a href="channel_box.php?i=<?php echo $a_name['id'];?>" class="btn btn-primary" role="button">Boxes</a>
						<a href="../hls/media/<?php echo "{$a_name['username']}"?>.m3u8" class="btn btn-primary" role="button">box-IOS</a>


						<span style="float:right" class="glyphicon glyphicon-eye-open" aria-hidden="true">
							<small id="<?php echo $a_name['id'];?>">
								<?php //echo ' '."{$a_name['number']}"?>
								<script src="http://code.jquery.com/jquery-latest.min.js"></script>
								<script>
								function get_number_<?php echo $a_name['id'];?>(channel_id){
								  $.ajax({
								      type : "POST",
								      url : "php/get_channel_number.php",
								      data : {

								        'id' : 	<?php echo $a_name['id'];?>

								      },
								      dataType : 'html'
								    }).done(function(data) {
								      //成功的時候

								      setTimeout(get_number_<?php echo $a_name['id'];?>, 2000);
								      document.getElementById(<?php echo $a_name['id'];?>).innerText=data;
								      //console.log(data);



								    }).fail(function(jqXHR, textStatus, errorThrown) {
								      //失敗的時候
								      alert("有錯誤產生，請看 console log");
								      console.log(jqXHR.responseText);
								    });
								};
								</script>
								<script> get_number_<?php echo $a_name['id'];?>(<?php echo $a_name['id'];?>)</script>

							</small>
						</span>

					  </div>
					</div>
 				</div>

 			<?php endforeach; ?>
 		<?php else: ?>
 			<h1>沒有頻道</h1>

 		<?php endif; ?>




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
