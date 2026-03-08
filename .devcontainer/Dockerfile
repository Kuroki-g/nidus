# syntax=docker/dockerfile:1
# check=error=true
FROM python:3.14-slim

ARG USER=vscode
ARG UID=1000
ARG GID=1000

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
  make \
  nano \
  socat \
  tree \
  unzip \
  xclip \
  zip \
  # Rust
  g++ \
  gcc \
  libc6-dev \
  libssl-dev \
  libonig-dev \
  mold \
  pkg-config \
  libprotobuf-dev \
  protobuf-compiler \
  ripgrep \
  xxd \
  # Process / debug tools
  procps \
  htop \
  gdb \
  strace \
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

ENV PATH="/home/${USER}/.local/bin:$PATH" \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  TERM=xterm-256color \
  # Rust
  RUSTUP_HOME="/home/${USER}/.rustup" \
  CARGO_HOME="/home/${USER}/.cargo" \
  PATH="/home/${USER}/.cargo/bin:${PATH}" \
  LANG=C.UTF-8

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
  | sh -s -- -y --default-toolchain stable

RUN cargo install sccache

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
  echo "alias clip='xclip -selection clipboard'" >> $HOME/.bashrc

RUN curl -fsSL https://claude.ai/install.sh | bash

WORKDIR /workspace

CMD ["bash"]
