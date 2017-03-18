broker_url = 'redis://localhost:6379/0'
result_backend = broker_url
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
enable_utc = True
imports = ["server.tasks"]
task_routes = {'server.tasks.send_media_to_box':{'queue':'send_queue'},
               'server.tasks.send_media_box_update':{'queue':'send_queue'}}