
FROM ubuntu:15.10
MAINTAINER fclaerhout.fr

# install maven build environment
RUN apt-get update
RUN apt-get -y install git openjdk-8-jdk maven python-pip
RUN pip install git+https://github.com/fclaerho/buildstack.git
# FIX java.security.InvalidAlgorithmParameterException
RUN update-ca-certificates -f

# test 1
WORKDIR /tmp
RUN git clone https://github.com/square/retrofit.git
WORKDIR /tmp/retrofit
RUN buildstack -v clean compile

# test 2
WORKDIR /tmp
RUN git clone https://github.com/jcsirot/jenerator.git
WORKDIR /tmp/jenerator
RUN buildstack -v clean compile
