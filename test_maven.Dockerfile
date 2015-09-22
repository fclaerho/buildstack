
FROM ubuntu:15.10
MAINTAINER fclaerhout.fr

# install maven build environment
RUN apt-get update
RUN apt-get -y install git maven python-pip
RUN pip install buildstack

# test 1
WORKDIR /tmp
RUN git clone https://github.com/square/retrofit.git
WORKDIR /tmp/retrofit
RUN buildstack clean compile
