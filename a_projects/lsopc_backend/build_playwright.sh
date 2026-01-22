#!/bin/bash

cur_path=$(pwd)
PROC_NAME=$(echo "${cur_path}"|awk -F"/" '{print $NF}')
echo "$PROC_NAME"
cur_time=$(date +"%Y%m%d%H%M")
VERSION=v.${cur_time}

# shellcheck disable=SC1090
source ~/.build_env.sh
#git pull

echo "docker build -t ${PROC_NAME}:${VERSION}" .
docker buildx build --platform linux/amd64 -t "${PROC_NAME}":"${VERSION}" .


