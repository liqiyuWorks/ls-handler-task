#!/bin/bash

cur_path=$(pwd)
PROC_NAME="fuel_predict"
echo "$PROC_NAME"
cur_time=$(date +"%Y%m%d%H%M")
VERSION=v.${cur_time}

#git pull

echo "docker build -t ${PROC_NAME}:${VERSION}" .
docker buildx build --platform linux/amd64 -t "${PROC_NAME}":"${VERSION}" .

