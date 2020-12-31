FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

ENV LANG en_US.UTF-8

ENV USER user
ENV HOME /home/${USER}

RUN useradd -d ${HOME} -m ${USER} && \
    passwd -d ${USER} && \
    adduser ${USER} sudo

RUN apt-get update && \
    apt-get install -y -q --no-install-recommends \
    ca-certificates \
    curl \
    git \
    usbutils \
    android-tools-* \
    fastboot \
    python \
    python-dev \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

USER ${USER}
WORKDIR ${HOME}

RUN git clone https://github.com/GramAddict/bot.git ./gramaddict
RUN pip3 install --no-cache-dir -r ./gramaddict/requirements.txt

WORKDIR ./gramaddict

COPY config.yml ./

USER root
COPY ./docker-entrypoint.sh ./
RUN chmod +x ./docker-entrypoint.sh

USER ${USER}
ENTRYPOINT ["./docker-entrypoint.sh"]