# The container docs/demo.gif is recorded in: a stock Ubuntu with bash-camp pitched into it. Build
# from the repository root:
#   docker build -t bash-camp-demo -f docs/demo/Dockerfile .
FROM ubuntu:24.04

# bash-camp's requirements and nothing more, so pixi brings tmux and make. procps for `watch`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl git procps python3 tar \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash camper
USER camper
WORKDIR /home/camper

COPY --chown=camper . /tmp/bash-camp
RUN python3 /tmp/bash-camp/bootstrap.py pitch && rm -rf /tmp/bash-camp

COPY --chown=camper docs/demo/props.sh /tmp/props.sh
RUN bash /tmp/props.sh && rm /tmp/props.sh

ENV TERM=xterm-256color COLORTERM=truecolor
CMD ["bash"]
