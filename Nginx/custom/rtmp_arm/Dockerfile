FROM nginx:stable-alpine

RUN apk add --no-cache \
    build-base \
    pcre-dev \
    openssl-dev \
    zlib-dev \
    git \
    linux-headers \
    wget

WORKDIR /tmp

RUN git clone https://github.com/arut/nginx-rtmp-module.git

RUN wget http://nginx.org/download/nginx-1.24.0.tar.gz && \
    tar -zxvf nginx-1.24.0.tar.gz && \
    cd nginx-1.24.0 && \
    ./configure --with-http_ssl_module --add-module=../nginx-rtmp-module && \
    make && make install

COPY nginx.conf /usr/local/nginx/conf/nginx.conf

EXPOSE 1935

CMD ["/usr/local/nginx/sbin/nginx", "-g", "daemon off;"]