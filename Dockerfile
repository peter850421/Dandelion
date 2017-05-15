FROM ubuntu:16.04

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y build-essential wget libpcre3 libpcre3-dev libssl-dev

# Install Redis
RUN cd /tmp && \
    wget http://download.redis.io/redis-stable.tar.gz && \
    tar xvzf redis-stable.tar.gz && \
    cd redis-stable && \
    make && \
    make install && \
    cp -f src/redis-sentinel /usr/local/bin && \
    mkdir -p /etc/redis && \
    cp -f *.conf /etc/redis && \
    rm -rf /tmp/redis-stable* && \
    sed -i 's/^\(bind .*\)$/# \1/' /etc/redis/redis.conf && \
    sed -i 's/^\(daemonize .*\)$/# \1/' /etc/redis/redis.conf && \
    sed -i 's/^\(dir .*\)$/# \1\ndir \/data/' /etc/redis/redis.conf && \
    sed -i 's/^\(logfile .*\)$/# \1/' /etc/redis/redis.conf && \
    redis-server --daemonize yes 

# Install Nginx
RUN wget http://nginx.org/download/nginx-1.10.2.tar.gz && \
    tar xvf nginx-1.10.2.tar.gz && \
    cd nginx-1.10.2 && \
    ./configure && \
    make && \
    make install

# Install python3.6
RUN \
    apt-get install -y software-properties-common curl \
    && add-apt-repository -y ppa:jonathonf/python-3.6 \
    && apt-get remove -y software-properties-common \
    && apt autoremove -y \
    && apt-get update \
    && apt-get install -y python3.6 \
    && curl -o /tmp/get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
    && python3.6 /tmp/get-pip.py \
    && apt-get remove -y curl \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get update \
    && apt-cache policy libexpat1 \
    && apt-get install -y python3.6-dev


RUN mkdir /dandelion

COPY . /dandelion

WORKDIR /dandelion

RUN pip3 install -r requirements.txt && \
    python3.6 setup.py install && \
    cp -f nginx.conf /usr/local/nginx/conf/nginx.conf

EXPOSE 8000

#CMD [ "/bin/sh", "-c", "python3.6 run_box.py"]
