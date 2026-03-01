# syntax=docker/dockerfile:1
# check=error=true
FROM python:3.14-slim

ARG USER=vscode
ARG UID=1000
ARG GID=1000
ARG NODE_MAJOR=22

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  bash-completion \
  ca-certificates \
  curl \
  git \
  gnupg \
  iproute2 \
  jq \
  less \
  lsof \
  nano \
  socat \
  tree \
  unzip \
  xclip \
  zip \
  && rm -rf /var/lib/apt/lists/*

# --- Create non root user ---
RUN groupadd --gid ${GID} ${USER} \
  && useradd \
  --uid ${UID} \
  --gid ${GID} \
  --shell /bin/bash \
  --create-home \
  ${USER}
RUN mkdir -p /workspace && chown ${UID}:${GID} /workspace

USER ${USER}
RUN curl -fsSL https://claude.ai/install.sh | bash

WORKDIR /workspace

ENV PIP_USER=1 \
  PATH="/home/${USER}/.local/bin:$PATH" \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  TERM=xterm-256color \
  LANG=C.UTF-8

RUN pip install --no-cache-dir uv && \
  echo "alias clip='xclip -selection clipboard'" >> $HOME/.bashrc

CMD ["bash"]
