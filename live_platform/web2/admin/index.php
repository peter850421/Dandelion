<?php 
require_once'../php/live_stream_db.php';
require_once'../php/function.php';
//print_r($_SESSION);
if(!isset($_SESSION['is_login']) || !$_SESSION['is_login'] )
{
	header("Location:login.php");
}
$data = get_user_channel($_SESSION['login_user_id']);

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
<script type="text/javascript" src="https://cdn.jsdelivr.net/clipboard.js/1.6.0/clipboard.min.js"></script>

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
 			<div class="col-xs-12" >
 				
 				<table class="table table-hover">
 					<tr>
 						<th>帳戶名稱</th>
 						<th>是否發布</th>
 						<th>頻道資訊</th>
 						<th>觀看人數</th>
 						<th>管理動作</th>
 					</tr>
 					<?php if(!empty($data)):?>
 						<td><?php echo $data['username']; ?></td>	
 						<td><?php echo $data['publish']?'發布中':'未發布';?></td>	
 						<td><?php echo $data['info'] ;?></td>	
 						<td><?php echo $data['number'] ;?></td>	
 						<td><a href="channel_editor.php?i=<?php echo $data['user_id'];//user_id ?>" class="btn btn-success">編輯</a></td>
 						
 					<?php else: ?>
 						<td colspan="5">無資料，請向管理員確認。</td>
 					<?php endif; ?>
				</table>
				<div class="panel panel-primary">
				  <div class="panel-heading">
				  	<div class="row">
						<div class="col-xs-5 " >
							<h4>直播金鑰</h4>
						</div>
						<div class="col-xs-1 col-xs-offset-4" >
						<script type="text/javascript">  
								var clipboard = new Clipboard('.btn');
								clipboard.on('success', function(e) {
									//console.info('Action:', e.action);
									//console.info('Text:', e.text);
									//console.info('Trigger:', e.trigger);

									e.clearSelection();
								});

								clipboard.on('error', function(e) {
									console.error('Action:', e.action);
									console.error('Trigger:', e.trigger);
								});
						</script> 
							<button  type="button" class="btn btn-default" data-clipboard-action="copy" data-clipboard-target="#publish_key">Copy </button>
						</div>
					</div>
				  </div>
				  <div class="panel-body" >
			  		<div class="span10">
				  		<p class = "publish_key" id='publish_key'><?php echo $data['username'].'?n='.$data['username'].'&key='.$data['publish_key'] ;?> 
					  	</p>
					</div>	
				  </div>
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


