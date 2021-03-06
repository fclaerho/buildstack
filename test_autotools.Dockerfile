
FROM ubuntu:15.10
MAINTAINER fclaerhout.fr

# install build environment
RUN apt-get update
RUN apt-get -y install git build-essential autoconf automake libtool python-pip
ENV fix 201509221703
RUN pip install git+https://github.com/fclaerho/buildstack.git

# test 1
WORKDIR /tmp
RUN git clone https://github.com/orangeduck/ptest
WORKDIR /tmp/ptest
RUN buildstack -vf Makefile clean compile
RUN test -e example
RUN test -e example2

# test 2
WORKDIR /tmp
RUN git clone https://github.com/andikleen/snappy-c
WORKDIR /tmp/snappy-c
RUN buildstack -v clean compile
RUN test -e scmd
RUN test -e sgverify
RUN test -e verify

# test 3
WORKDIR /tmp
RUN git clone https://github.com/maxmind/geoip-api-c
WORKDIR /tmp/geoip-api-c
RUN buildstack -vf configure.ac clean compile
RUN test -e apps/geoiplookup
RUN test -e apps/geoiplookup6

# test 4
# automake fails due to a missing macro; issue reported
# https://github.com/vlm/asn1c

# test 5
# FAILS: make all, target all not found
#WORKDIR /tmp
#RUN git clone https://github.com/git/git
#WORKDIR /tmp/git
#RUN buildstack -v clean compile
#RUN test -e git

# test 6
# not a standard process! no Makefile.am so install-sh touch'ed manually >=|
# https://github.com/php/php-src

# test 7
WORKDIR /tmp
RUN git clone https://github.com/bagder/curl
WORKDIR /tmp/curl
RUN buildstack -f configure.ac -v clean compile
RUN test -e src/curl

# test 8
WORKDIR /tmp
RUN git clone https://github.com/twitter/twemproxy
WORKDIR /tmp/twemproxy
RUN buildstack -v clean compile
RUN test -e src/nutcracker

# test 9
# FAILS: configure.ac:108: error: possibly undefined macro: AC_SEARCH_LIBS
#WORKDIR /tmp
#RUN apt-get -y install libevent-dev libncurses5-dev
#RUN git clone https://github.com/tmux/tmux
#WORKDIR /tmp/tmux
#RUN buildstack -v clean compile
#RUN test -e tmux
