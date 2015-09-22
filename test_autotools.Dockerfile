
FROM ubuntu:15.10
MAINTAINER fclaerhout.fr

# install build environment
RUN apt-get update
RUN apt-get -y install git build-essential autoconf automake python-pip
RUN pip install git+https://github.com/fclaerho/buildstack.git

# test 1
WORKDIR /tmp
RUN git clone https://github.com/orangeduck/ptest
WORKDIR /tmp/ptest
RUN buildstack clean compile
RUN test -e example
RUN test -e example2

# test 2
WORKDIR /tmp
RUN git clone https://github.com/andikleen/snappy-c
WORKDIR /tmp/snappy-c
RUN buildstack clean compile
RUN test -e scmd
RUN test -e sgverify
RUN test -e verify

# test 3
WORKDIR /tmp
RUN git clone https://github.com/maxmind/geoip-api-c
WORKDIR /tmp/geoip-api-c
RUN buildstack clean compile
RUN test -e apps/geoiplookup
RUN test -e apps/geoiplookup6

# test 4
# automake fails due to a missing macro; issue reported
# https://github.com/vlm/asn1c

# test 5
WORKDIR /tmp
RUN git clone https://github.com/git/git
WORKDIR /tmp/git
RUN buildstack clean compile
RUN test -e git

# test 6
# not a standard process! no Makefile.am so install-sh touch'ed manually >=|
# https://github.com/php/php-src

# test 7
WORKDIR /tmp
RUN git clone https://github.com/bagder/curl
WORKDIR /tmp/curl
RUN buildstack clean compile
RUN test -e src/curl

# test 8
WORKDIR /tmp
RUN git clone https://github.com/twitter/twemproxy
WORKDIR /tmp/twemproxy
RUN buildstack clean compile
RUN test -e src/nutcracker

# test 9
WORKDIR /tmp
RUN sudo apt-get -y installlibevent-dev libncurses5-dev
RUN git clone https://github.com/tmux/tmux
WORKDIR /tmp/tmux
RUN buildstack clean compile
RUN test -e tmux
