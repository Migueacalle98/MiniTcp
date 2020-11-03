FROM ubuntu:18.04

USER root
WORKDIR /root

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    iputils-ping \
    mininet \
    net-tools \
    openvswitch-switch \
    openvswitch-testcontroller \
    tcpdump \
    vim \
    x11-xserver-utils \
    xterm \
    python3.7 \
    python3.7-dev \
 && rm -rf /var/lib/apt/lists/*

EXPOSE 6633 6653 6640

ENTRYPOINT ["/entrypoint.sh"]
