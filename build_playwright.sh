#!/bin/bash

cur_path=$(pwd)
PROC_NAME=$(echo "${cur_path}"|awk -F"/" '{print $NF}')
echo "$PROC_NAME"
cur_time=$(date +"%Y%m%d%H%M")
VERSION=v.${cur_time}

# shellcheck disable=SC1090
source ~/.build_env.sh
docker login -u "${ALI_USER}" -p "${ALI_PASSWORD}" "${ALI_DOMAIN}"

#git pull

echo "docker build -t ${PROC_NAME}:${VERSION}" .
docker buildx build --platform linux/amd64 -f Dockerfile_playwright -t "${PROC_NAME}":"${VERSION}" .

image_id=$(docker images|grep "${PROC_NAME}"|grep "${VERSION}"|grep -v registry|awk '{print $3}')
echo "image_id $image_id"

echo "docker tag ${image_id} ${ALI_DOMAIN}/${ALI_SPACE}/${PROC_NAME}:${VERSION}"
docker tag "${image_id}" "${ALI_DOMAIN}"/"${ALI_SPACE}"/"${PROC_NAME}":"${VERSION}"
echo "docker push ${ALI_DOMAIN}/${ALI_SPACE}/${PROC_NAME}:${VERSION}"
docker push "${ALI_DOMAIN}"/"${ALI_SPACE}"/"${PROC_NAME}":"${VERSION}"

