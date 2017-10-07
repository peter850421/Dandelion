FROM nginx:1.13

ADD compose/entrance/nginx/nginx.conf /etc/nginx/nginx.conf
ADD compose/cert/server.crt /etc/ssl/server.crt
ADD compose/cert/server.key /etc/ssl/server.key

CMD ["nginx", "-g", "daemon off;"]
