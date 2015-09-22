
FROM ubuntu:15.10
MAINTAINER fclaerhout.fr

# install maven build environment
RUN apt-get update
RUN apt-get -y install git openjdk-8-jdk maven python-pip
RUN update-ca-certificates -f
RUN pip install git+https://github.com/fclaerho/buildstack.git

# test 1
WORKDIR /tmp
RUN git clone https://github.com/square/retrofit.git
WORKDIR /tmp/retrofit
RUN buildstack -v clean compile
