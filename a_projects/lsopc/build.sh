#!/bin/bash

cur_path=$(pwd)
PROC_NAME="lsopc"
cur_time=$(date +"%Y%m%d%H%M")
VERSION=v.${cur_time}

# shellcheck disable=SC1090
source ~/.build_env.sh
docker login -u "${ALI_USER}" -p "${ALI_PASSWORD}" "${ALI_DOMAIN}"

#git pull

# Build the project
echo "Building project..."
npm run build
if [ $? -ne 0 ]; then
    echo "Frontend build failed"
    exit 1
fi

echo "docker build -t ${PROC_NAME}:${VERSION}" .
docker buildx build --platform linux/amd64 -t "${PROC_NAME}":"${VERSION}" .
if [ $? -ne 0 ]; then
    echo "Docker build failed"
    exit 1
fi

image_id=$(docker images -q "${PROC_NAME}:${VERSION}")
echo "image_id $image_id"

echo "docker tag ${image_id} ${ALI_DOMAIN}/${ALI_SPACE}/${PROC_NAME}:${VERSION}"
docker tag "${image_id}" "${ALI_DOMAIN}"/"${ALI_SPACE}"/"${PROC_NAME}":"${VERSION}"
echo "docker push ${ALI_DOMAIN}/${ALI_SPACE}/${PROC_NAME}:${VERSION}"
docker push "${ALI_DOMAIN}"/"${ALI_SPACE}"/"${PROC_NAME}":"${VERSION}"

