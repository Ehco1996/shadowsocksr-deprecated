FROM alpine:3.8
LABEL maintainer="Issacc<8qllyhy@gmail.com>"
RUN apk --no-cache add\
                        curl \
                        python3-dev \
                        libsodium-dev \
                        openssl-dev \
                        udns-dev \
                        mbedtls-dev \
                        pcre-dev \
                        libev-dev \
                        libtool \
                        libffi-dev            && \
    apk add --no-cache --virtual .build-deps \
                        git \
                        make \
                        py3-pip \
                        autoconf \
                        automake \
                        build-base \
                        linux-headers         && \
     ln -s /usr/bin/python3 /usr/bin/python   && \
     ln -s /usr/bin/pip3    /usr/bin/pip      && \
     git clone https://github.com/Ehco1996/shadowsocksr.git "/root/shadowsocks" --depth 1 && \
     cd  /root/shadowsocks                    && \
     pip install --upgrade pip                && \
     pip install -r requirements.txt          && \
     rm -rf ~/.cache && touch /etc/hosts.deny && \
     apk del --purge .build-deps

WORKDIR /root/shadowsocks

CMD python /root/shadowsocks/server.py
