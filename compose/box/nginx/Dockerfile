FROM armhfbuild/nginx

ADD compose/box/nginx/nginx.conf /etc/nginx/nginx.conf
ADD compose/cert/server.crt /etc/ssl/server.crt
ADD compose/cert/server.key /etc/ssl/server.key

CMD ["nginx", "-g", "daemon off;"]
