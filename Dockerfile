FROM ubuntu:16.10

RUN mkdir /dandelion

COPY . /dandelion

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y build-essential tcl wget libpcre3 libpcre3-dev libssl-dev

# Install Redis
RUN cd /tmp && \
    wget http://download.redis.io/redis-stable.tar.gz && \
    tar xvzf redis-stable.tar.gz && \
    cd redis-stable && \
    make && \
    make install && \
    cp -f src/redis-sentinel /usr/local/bin && \
    mkdir -p /etc/redis && \
    rm -rf /tmp/redis-stable* && \
    cp -f /dandelion/install/redis.conf /etc/redis/redis.conf && \
    touch /etc/systemd/system/redis.service && \
    printf "[Unit]\n\
Description=Redis In-Memory Data Store \n\
After=network.target\n\
\n\
[Service]\n\
User=root\n\
Group=root\n\
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf\n\
ExecStop=/usr/local/bin/redis-cli shutdown\n\
Restart=always\n\
\n\
[Install]\n\
WantedBy=multi-user.target\n">>/etc/systemd/system/redis.service && \
    mkdir -p /var/lib/redis
    
# Install Nginx
RUN wget http://nginx.org/download/nginx-1.10.2.tar.gz && \
    tar xvf nginx-1.10.2.tar.gz && \
    cd nginx-1.10.2 && \
    ./configure && \
    make && \
    make install && \
    cp -f /dandelion/install/nginx.conf /usr/local/nginx/conf/nginx.conf

# Install python3.6
RUN apt-get install -y software-properties-common curl \
    && add-apt-repository -y ppa:jonathonf/python-3.6 \
    && apt-get remove -y software-properties-common \
    && apt-get autoremove -y \
    && apt-get update \
    && apt-get install -y python3.6 \
    && curl -o /tmp/get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
    && python3.6 /tmp/get-pip.py \
    && apt-get remove -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get update \
    && apt-cache policy libexpat1 \
    && apt-get install -y python3.6-dev

WORKDIR /dandelion

EXPOSE 8000

#CMD [ "/bin/sh", "-c", "python3.6 run_box.py"]
