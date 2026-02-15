# -*- coding: utf-8 -*-
"""VEO 3.1 视频生成异步服务（文生视频、单帧图生视频、多帧图生视频）"""

import json
import logging
import os
import re
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 视频文件保存目录（与 main.py 中 static 挂载一致）
STATIC_VIDEOS_DIR = "static/videos"


def _safe_json(resp: httpx.Response, context: str = "") -> dict:
    """
    安全解析 JSON 响应。若响应为空或非 JSON，记录日志并抛出明确异常。
    部分上游 API 在任务未就绪时可能返回 200 但 body 为空或 HTML。
    """
    text = (resp.text or "").strip()
    if not text:
        logger.warning("[VEO] %s 响应体为空 status=%d", context, resp.status_code)
        raise ValueError("上游 API 返回空响应，视频可能尚未就绪，请稍后重试")
    try:
        return resp.json()
    except json.JSONDecodeError as e:
        preview = text[:300] if len(text) > 300 else text
        logger.warning("[VEO] %s 响应非 JSON status=%d preview=%s", context, resp.status_code, preview)
        raise ValueError("上游 API 返回格式异常，请稍后重试") from e


class VEOClient:
    """VEO 3.1 异步视频生成客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        # 与图片生成共用 API Key（GEMINI_API_KEY），VEO_API_KEY 可选覆盖
        self.api_key = (api_key or settings.VEO_API_KEY or settings.GEMINI_API_KEY).strip()
        self.base_url = (base_url or settings.VEO_BASE_URL).rstrip("/")
        # 参考官方 curl：Authorization: Bearer sk-xxx
        auth_val = self.api_key if self.api_key.lower().startswith("bearer ") else f"Bearer {self.api_key}"
        self.headers = {
            "Authorization": auth_val,
            "Accept": "application/json",
        }
        self.timeout = settings.VEO_TIMEOUT

    async def _post_json(self, url: str, json_data: dict) -> dict:
        """POST JSON 请求"""
        headers = {**self.headers, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=json_data)
            resp.raise_for_status()
            return _safe_json(resp, "create")

    async def _post_multipart(self, url: str, data: dict, files: list) -> dict:
        """POST multipart/form-data 请求"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self.headers, data=data, files=files)
            resp.raise_for_status()
            return _safe_json(resp, "create")

    async def create_video_text(
        self,
        prompt: str,
        model: str = "veo-3.1",
    ) -> str:
        """文生视频：创建任务，返回 video_id"""
        url = f"{self.base_url}/v1/videos"
        payload = {"prompt": prompt, "model": model}
        result = await self._post_json(url, payload)
        video_id = result.get("id")
        if not video_id:
            raise ValueError(f"VEO API 未返回 video_id: {result}")
        logger.info("[VEO] 文生视频任务已创建, video_id=%s", video_id)
        return video_id

    async def create_video_single_image(
        self,
        prompt: str,
        image_bytes: bytes,
        filename: str = "image.jpg",
        mime_type: str = "image/jpeg",
        model: str = "veo-3.1-landscape-fl",
    ) -> str:
        """单帧图生视频：以一张图片作为首帧"""
        url = f"{self.base_url}/v1/videos"
        data = {"prompt": prompt, "model": model}
        files = [("input_reference", (filename, image_bytes, mime_type))]
        result = await self._post_multipart(url, data, files)
        video_id = result.get("id")
        if not video_id:
            raise ValueError(f"VEO API 未返回 video_id: {result}")
        logger.info("[VEO] 单帧图生视频任务已创建, video_id=%s", video_id)
        return video_id

    async def create_video_dual_images(
        self,
        prompt: str,
        image_first_bytes: bytes,
        image_last_bytes: bytes,
        filename_first: str = "first.jpg",
        filename_last: str = "last.jpg",
        mime_type: str = "image/jpeg",
        model: str = "veo-3.1-landscape-fl",
    ) -> str:
        """多帧图生视频：首尾双图，AI 生成中间过渡"""
        url = f"{self.base_url}/v1/videos"
        data = {"prompt": prompt, "model": model}
        files = [
            ("input_reference", (filename_first, image_first_bytes, mime_type)),
            ("input_reference", (filename_last, image_last_bytes, mime_type)),
        ]
        result = await self._post_multipart(url, data, files)
        video_id = result.get("id")
        if not video_id:
            raise ValueError(f"VEO API 未返回 video_id: {result}")
        logger.info("[VEO] 多帧图生视频任务已创建, video_id=%s", video_id)
        return video_id

    async def get_status(self, video_id: str) -> dict:
        """查询任务状态。建议每 5～10 秒轮询一次，直到 status 为 completed 或 failed"""
        url = f"{self.base_url}/v1/videos/{video_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return _safe_json(resp, "get_status")

    async def get_content(self, video_id: str) -> dict:
        """
        获取视频内容。参考官方：GET /v1/videos/{video_ID}/content，Authorization: Bearer sk-xxx。
        上游可能返回：① JSON（含 url、resolution）；② 视频文件二进制（--output video.mp4）。
        """
        url = f"{self.base_url}/v1/videos/{video_id}/content"
        # 不强制 Accept: application/json，以便上游返回视频文件时能拿到 binary
        headers = {"Authorization": self.headers["Authorization"]}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            content_type = (resp.headers.get("Content-Type") or "").lower()
            # 1）上游直接返回视频文件（curl --output video.mp4）
            if "video/" in content_type or "application/octet-stream" in content_type:
                os.makedirs(STATIC_VIDEOS_DIR, exist_ok=True)
                safe_id = re.sub(r"[^\w\-]", "_", video_id)
                filename = f"{safe_id}.mp4"
                filepath = os.path.join(STATIC_VIDEOS_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                url_path = f"/static/videos/{filename}"
                logger.info("[VEO] get_content 已保存视频文件 video_id=%s path=%s", video_id, url_path)
                return {"url": url_path, "resolution": None}
            # 2）空响应：检查重定向 Location
            if not resp.content:
                loc = resp.headers.get("Location") or resp.headers.get("Content-Location")
                if loc:
                    return {"url": loc, "resolution": None}
                raise ValueError("视频内容为空，请稍后重试")
            # 3）按 JSON 解析
            text = (resp.text or "").strip()
            if "text/html" in content_type or text.lstrip().lower().startswith(("<!doctype", "<html")):
                preview_len = min(len(text), 800)
                logger.warning(
                    "[VEO] get_content 返回 HTML video_id=%s content_type=%s preview=%s",
                    video_id, content_type, text[:preview_len],
                )
                raise ValueError("视频服务返回了 HTML 页面，请检查 video_id 是否有效或联系 api.apiyi.com 确认。")
            try:
                data = resp.json()
                return data if isinstance(data, dict) else {"url": str(data), "resolution": None}
            except json.JSONDecodeError:
                if text.startswith("http"):
                    return {"url": text.strip(), "resolution": None}
                raise ValueError("视频内容返回格式异常，请稍后重试")


veo_client = VEOClient()
