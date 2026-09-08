import os
import json
import base64
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

app = FastAPI(title="ImageGen Proxy API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Session
SESSION = requests.Session()
SESSION.mount("https://", requests.adapters.HTTPAdapter(max_retries=5))

# 用户请求记录（简化版，生产环境建议用Redis）
user_requests: dict = {}


# ==================== 数据模型 ====================

class TextToImageRequest(BaseModel):
    prompt: str
    n: int = 1
    size: str = "4:3"
    resolution: str = "4k"
    reference_image: Optional[str] = None  # base64或URL


class ImageToImageRequest(BaseModel):
    prompt: str
    image: str  # base64编码的图片
    n: int = 1
    size: str = "4:3"
    resolution: str = "4k"


class GenerateResponse(BaseModel):
    success: bool
    task_id: Optional[str] = None
    images: Optional[list] = None
    error: Optional[str] = None


# ==================== 工具函数 ====================

def image_to_data_url(path_or_base64: str) -> str:
    """将图片路径或base64转换为data URL"""
    if path_or_base64.startswith("data:"):
        return path_or_base64

    if path_or_base64.startswith("http"):
        return path_or_base64

    # 假设是纯base64
    return f"data:image/png;base64,{path_or_base64}"


def get_client_id(authorization: Optional[str] = Header(None)) -> str:
    """获取客户端标识（简化版）"""
    if authorization:
        return authorization
    return "anonymous"


def check_rate_limit(client_id: str) -> bool:
    """检查请求频率限制"""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{client_id}:{today}"

    count = user_requests.get(key, 0)
    if count >= settings.DAILY_LIMIT:
        return False

    user_requests[key] = count + 1
    return True


def poll_task(task_id: str, headers: dict, interval: int = 5, timeout: int = 600) -> Optional[dict]:
    """轮询任务状态"""
    url = f"{settings.APIMART_API_BASE}/v1/tasks/{task_id}"
    time.sleep(15)
    elapsed = 15

    while elapsed < timeout:
        try:
            resp = SESSION.get(url, headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            time.sleep(interval)
            elapsed += interval
            continue

        inner = data.get("data", {})
        if not isinstance(inner, dict):
            inner = {}

        status = inner.get("status", "")
        if status == "completed":
            return inner
        elif status == "failed":
            err = inner.get("error", {})
            raise Exception(err.get("message", "Task failed"))

        time.sleep(interval)
        elapsed += interval

    raise Exception(f"Timeout after {timeout}s")


def extract_urls(result: dict) -> list:
    """从响应中提取图片URL"""
    urls = []
    images = []

    result_data = result.get("result", {})
    if isinstance(result_data, dict):
        images = result_data.get("images", [])

    if not images:
        images = result.get("images", [])

    if not images:
        images = result.get("data", [])
        if isinstance(images, dict):
            images = [images]

    for item in images:
        if not isinstance(item, dict):
            continue
        url_val = item.get("url")
        if isinstance(url_val, list):
            urls.extend(url_val)
        elif isinstance(url_val, str):
            urls.append(url_val)
        elif "b64_json" in item:
            urls.append(("b64", item["b64_json"]))

    return urls


def download_image(url: str, filepath: Path) -> bool:
    """下载图片"""
    for attempt in range(5):
        try:
            r = SESSION.get(url, timeout=120)
            filepath.write_bytes(r.content)
            return True
        except Exception:
            pass
    return False


def cleanup_old_images():
    """清理过期图片"""
    if not settings.IMAGE_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(hours=settings.IMAGE_RETENTION_HOURS)

    for file in settings.IMAGE_DIR.glob("*"):
        if file.is_file():
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff:
                file.unlink()


# ==================== API路由 ====================

@app.get("/")
async def root():
    return {"message": "ImageGen Proxy API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/generate/text")
async def text_to_image(
    request: TextToImageRequest,
    authorization: Optional[str] = Header(None)
):
    """文生图接口"""
    if not settings.APIMART_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    # 频率限制
    client_id = get_client_id(authorization)
    if not check_rate_limit(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded ({settings.DAILY_LIMIT} requests/day)"
        )

    # 构建请求
    payload = {
        "model": "gpt-image-2",
        "prompt": request.prompt,
        "n": request.n,
        "size": request.size,
        "resolution": request.resolution,
        "official_fallback": False,
    }

    if request.reference_image:
        payload["image_urls"] = [image_to_data_url(request.reference_image)]

    headers = {
        "Authorization": f"Bearer {settings.APIMART_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = SESSION.post(
            f"{settings.APIMART_API_BASE}/v1/images/generations",
            json=payload,
            headers=headers,
            timeout=120
        )
        data = response.json()

        if response.status_code not in (200, 202):
            raise HTTPException(status_code=response.status_code, detail=data)

        # 检查是否异步任务
        inner = data.get("data", {})
        if isinstance(inner, list) and inner:
            inner = inner[0]
        task_id = data.get("task_id") or (inner.get("task_id") if isinstance(inner, dict) else None)

        if task_id:
            result = poll_task(task_id, headers)
        else:
            result = data

        # 提取图片URL
        urls = extract_urls(result)
        if not urls:
            raise HTTPException(status_code=500, detail="No images in response")

        # 保存图片并返回URL
        settings.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_images = []

        for i, url_or_b64 in enumerate(urls, 1):
            filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{i}.png"
            filepath = settings.IMAGE_DIR / filename

            if isinstance(url_or_b64, tuple) and url_or_b64[0] == "b64":
                filepath.write_bytes(base64.b64decode(url_or_b64[1]))
            else:
                if not download_image(url_or_b64, filepath):
                    continue

            saved_images.append(f"/images/{filename}")

        return {"success": True, "images": saved_images}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/image")
async def image_to_image(
    request: ImageToImageRequest,
    authorization: Optional[str] = Header(None)
):
    """图生图接口"""
    if not settings.APIMART_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    # 频率限制
    client_id = get_client_id(authorization)
    if not check_rate_limit(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded ({settings.DAILY_LIMIT} requests/day)"
        )

    # 构建请求
    payload = {
        "model": "gpt-image-2",
        "prompt": request.prompt,
        "n": request.n,
        "size": request.size,
        "resolution": request.resolution,
        "image_urls": [image_to_data_url(request.image)],
        "official_fallback": False,
    }

    headers = {
        "Authorization": f"Bearer {settings.APIMART_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = SESSION.post(
            f"{settings.APIMART_API_BASE}/v1/images/generations",
            json=payload,
            headers=headers,
            timeout=120
        )
        data = response.json()

        if response.status_code not in (200, 202):
            raise HTTPException(status_code=response.status_code, detail=data)

        # 检查是否异步任务
        inner = data.get("data", {})
        if isinstance(inner, list) and inner:
            inner = inner[0]
        task_id = data.get("task_id") or (inner.get("task_id") if isinstance(inner, dict) else None)

        if task_id:
            result = poll_task(task_id, headers)
        else:
            result = data

        # 提取图片URL
        urls = extract_urls(result)
        if not urls:
            raise HTTPException(status_code=500, detail="No images in response")

        # 保存图片并返回URL
        settings.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_images = []

        for i, url_or_b64 in enumerate(urls, 1):
            filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{i}.png"
            filepath = settings.IMAGE_DIR / filename

            if isinstance(url_or_b64, tuple) and url_or_b64[0] == "b64":
                filepath.write_bytes(base64.b64decode(url_or_b64[1]))
            else:
                if not download_image(url_or_b64, filepath):
                    continue

            saved_images.append(f"/images/{filename}")

        return {"success": True, "images": saved_images}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task/{task_id}")
async def check_task(task_id: str):
    """查询任务状态"""
    if not settings.APIMART_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    headers = {"Authorization": f"Bearer {settings.APIMART_API_KEY}"}

    try:
        resp = SESSION.get(
            f"{settings.APIMART_API_BASE}/v1/tasks/{task_id}",
            headers=headers,
            timeout=30
        )
        data = resp.json()
        inner = data.get("data", {})
        if not isinstance(inner, dict):
            inner = {}
        return inner
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sizes")
async def get_sizes():
    """获取支持的尺寸选项"""
    return {
        "sizes": [
            {"value": "1:1", "label": "1:1 正方形"},
            {"value": "4:3", "label": "4:3 横版"},
            {"value": "3:4", "label": "3:4 竖版"},
            {"value": "16:9", "label": "16:9 宽屏"},
            {"value": "9:16", "label": "9:16 竖屏"},
        ],
        "resolutions": [
            {"value": "4k", "label": "4K 高清"},
            {"value": "2k", "label": "2K"},
            {"value": "1k", "label": "1K"},
        ]
    }


# 静态文件服务（图片）
app.mount("/images", StaticFiles(directory=settings.IMAGE_DIR), name="images")

# 启动定时清理任务
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_images, "interval", hours=1)
scheduler.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
