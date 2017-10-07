FROM armhfbuild/nginx

ADD nginx.conf /etc/nginx/nginx.conf
ADD server.crt /etc/ssl/server.crt
ADD server.key /etc/ssl/server.key

CMD ["nginx", "-g", "daemon off;"]
