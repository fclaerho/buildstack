
FROM ubuntu:15.10
MAINTAINER fclaerhout.fr
USER ubuntu

# install maven build environment
RUN sudo apt-get install git maven python-pip
RUN sudo pip install buildstack

# test 1
WORKDIR /tmp
RUN git clone https://github.com/square/retrofit.git
WORKDIR /tmp/retrofit
RUN buildstack clean compile
