<?php
require_once'php/live_stream_db.php';
require_once'php/function.php';
$channel = get_channel($_GET['i']);
$client_id = get_client_id();
include ('configfile.php')  ;
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
 		 	<div class="col-xs-12 " >

				<div class="panel panel-success">
					 <div class="panel-heading">
						 <h3><?php echo "{$channel['username']}"?>
						 	<span style="float:right" class="glyphicon glyphicon-eye-open" aria-hidden="true">
									<small id="channel_number">
										<?php echo ' '."{$channel['number']}"?>
									</small>
							</span>
						</h3>
					 </div>
					 <div class="panel-body">
					 	<div class="embed-responsive embed-responsive-16by9">
							<?php if(!empty($channel)):?>
								<script src="https://cdn.jsdelivr.net/hls.js/latest/hls.min.js"></script>
								<video id="video" poster="<?php echo '../hls/'."{$channel['username']}"?>_src.png"  controls > </video>
								<script>
								  if(Hls.isSupported()) {
									var video = document.getElementById('video');
									var hls = new Hls();
									hls.loadSource(<?php echo "'http://{$Server_IP}/hls/media/{$channel['username']}.m3u8'"?>);
									hls.attachMedia(video);
									hls.on(Hls.Events.MANIFEST_PARSED,function() {
									  video.play();
								  });
								 }
								</script>
									<?php else: ?>
										<h1>沒有頻道</h1>

									<?php endif; ?>


						</div>
					 </div>
					 <div class="panel-footer"><?php echo "{$channel['info']}"?></div>

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
<script src="http://code.jquery.com/jquery-latest.min.js"></script>
<script>

$(document).on("ready",function worker(){

  $.ajax({
      type : "POST",
      url : "php/channel_number.php",
      data : {

        'id' : 	<?php echo $_GET['i'] ?>
				,'client_id' : "<?php echo $client_id?>"
      },
      dataType : 'html'
    }).done(function(data) {
      //成功的時候
			 document.getElementById('channel_number').innerText=data;
			setTimeout(worker, 2000);
      //console.log(data);



    }).fail(function(jqXHR, textStatus, errorThrown) {
      //失敗的時候
      alert("有錯誤產生，請看 console log");
      console.log(jqXHR.responseText);
    });



});
</script>
</body>
</html>
