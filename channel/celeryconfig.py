broker_url = 'redis://localhost:6379/0'
result_backend = broker_url
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
enable_utc = True
imports = ["server.tasks"]
result_expires = 1
