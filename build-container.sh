#!/bin/bash
set -e

docker build \
  --file docker/Dockerfile \
  -t nidus:latest .
