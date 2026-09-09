import os
import json
import base64
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import requests
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

app = FastAPI(title="ImageGen Proxy API", version="2.0.0")

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
    """文生图请求"""
    prompt: str = Field(..., description="图像生成的文本描述")
    n: int = Field(1, ge=1, le=4, description="生成图片张数")
    size: str = Field("1:1", description="图像比例")
    resolution: str = Field("1k", description="分辨率档位: 1k/2k/4k")
    reference_images: Optional[List[str]] = Field(None, description="参考图URL或base64")
    official_fallback: bool = Field(False, description="是否使用官方渠道兜底")


class ImageToImageRequest(BaseModel):
    """图生图请求"""
    prompt: str = Field(..., description="图像生成的文本描述")
    image: str = Field(..., description="参考图base64")
    n: int = Field(1, ge=1, le=4, description="生成图片张数")
    size: str = Field("1:1", description="图像比例")
    resolution: str = Field("1k", description="分辨率档位: 1k/2k/4k")
    official_fallback: bool = Field(False, description="是否使用官方渠道兜底")


class GenerateResponse(BaseModel):
    """生成响应"""
    success: bool
    task_id: Optional[str] = None
    images: Optional[list] = None
    error: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: Optional[int] = None
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
    """获取客户端标识"""
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


def save_image(url_or_b64, filename_prefix: str) -> Optional[str]:
    """保存图片并返回URL"""
    settings.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{filename_prefix}.png"
    filepath = settings.IMAGE_DIR / filename

    if isinstance(url_or_b64, tuple) and url_or_b64[0] == "b64":
        filepath.write_bytes(base64.b64decode(url_or_b64[1]))
        return f"/images/{filename}"
    elif isinstance(url_or_b64, str):
        if url_or_b64.startswith("data:"):
            # base64 data URL
            header, data = url_or_b64.split(",", 1)
            filepath.write_bytes(base64.b64decode(data))
            return f"/images/{filename}"
        else:
            # URL
            if download_image(url_or_b64, filepath):
                return f"/images/{filename}"
    return None


# ==================== API路由 ====================

@app.get("/")
async def root():
    return {"message": "ImageGen Proxy API", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/models")
async def get_models():
    """获取支持的模型列表"""
    return {
        "models": [
            {
                "id": "gpt-image-2",
                "name": "GPT-Image-2",
                "description": "OpenAI 官方模型，支持文生图/图生图/局部重绘",
                "features": ["text2img", "img2img", "inpaint", "multi_ref"],
                "max_images": 4,
                "max_ref_images": 15,
                "resolutions": ["1k", "2k", "4k"],
                "sizes": ["auto", "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16", "2:1", "1:2", "3:1", "1:3", "21:9", "9:21"]
            },
            {
                "id": "imagen-4.0-apimart",
                "name": "Imagen 4.0",
                "description": "Google Imagen 4，仅支持文生图",
                "features": ["text2img"],
                "max_images": 1,
                "max_ref_images": 0,
                "resolutions": ["2k"],
                "sizes": ["1:1", "4:3", "3:4", "16:9", "9:16"]
            },
            {
                "id": "seedream-4.5",
                "name": "Seedream 4.5",
                "description": "豆包模型，支持文生图/图生图/组图生成",
                "features": ["text2img", "img2img", "multi_ref"],
                "max_images": 15,
                "max_ref_images": 15,
                "resolutions": ["2k", "4k"],
                "sizes": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "auto"]
            },
            {
                "id": "seedream-5.0-lite",
                "name": "Seedream 5.0 Lite",
                "description": "豆包轻量版，支持文生图/图生图",
                "features": ["text2img", "img2img", "multi_ref"],
                "max_images": 15,
                "max_ref_images": 15,
                "resolutions": ["2k", "3k", "4k"],
                "sizes": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "auto"]
            },
            {
                "id": "flux-2-pro",
                "name": "Flux 2 Pro",
                "description": "Flux 2.0 Pro，支持文生图/图生图/多参考图融合",
                "features": ["text2img", "img2img", "multi_ref"],
                "max_images": 1,
                "max_ref_images": 8,
                "resolutions": ["1MP", "2MP", "3MP", "4MP"],
                "sizes": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "auto"]
            },
            {
                "id": "flux-2-max",
                "name": "Flux 2 Max",
                "description": "Flux 2.0 最高质量版本",
                "features": ["text2img", "img2img", "multi_ref"],
                "max_images": 1,
                "max_ref_images": 8,
                "resolutions": ["1MP", "2MP", "3MP", "4MP"],
                "sizes": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "auto"]
            }
        ]
    }


@app.get("/api/sizes")
async def get_sizes():
    """获取支持的尺寸选项"""
    return {
        "sizes": [
            {"value": "auto", "label": "自动"},
            {"value": "1:1", "label": "1:1 正方形"},
            {"value": "3:2", "label": "3:2 横版"},
            {"value": "2:3", "label": "2:3 竖版"},
            {"value": "4:3", "label": "4:3 横版"},
            {"value": "3:4", "label": "3:4 竖版"},
            {"value": "5:4", "label": "5:4 横版"},
            {"value": "4:5", "label": "4:5 竖版"},
            {"value": "16:9", "label": "16:9 宽屏"},
            {"value": "9:16", "label": "9:16 竖屏"},
            {"value": "2:1", "label": "2:1 横版"},
            {"value": "1:2", "label": "1:2 竖版"},
            {"value": "3:1", "label": "3:1 超宽"},
            {"value": "1:3", "label": "1:3 超长"},
            {"value": "21:9", "label": "21:9 电影宽屏"},
            {"value": "9:21", "label": "9:21 电影竖屏"},
        ],
        "resolutions": [
            {"value": "1k", "label": "1K 标准"},
            {"value": "2k", "label": "2K 高清"},
            {"value": "4k", "label": "4K 超高清"},
        ]
    }


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
        "official_fallback": request.official_fallback,
    }

    if request.reference_images:
        payload["image_urls"] = [image_to_data_url(img) for img in request.reference_images]

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
        saved_images = []
        for i, url_or_b64 in enumerate(urls, 1):
            img_path = save_image(url_or_b64, str(i))
            if img_path:
                saved_images.append(img_path)

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
        "official_fallback": request.official_fallback,
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
        saved_images = []
        for i, url_or_b64 in enumerate(urls, 1):
            img_path = save_image(url_or_b64, str(i))
            if img_path:
                saved_images.append(img_path)

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

        # 提取图片URL
        images = []
        if inner.get("status") == "completed":
            urls = extract_urls(inner)
            for i, url_or_b64 in enumerate(urls, 1):
                img_path = save_image(url_or_b64, str(i))
                if img_path:
                    images.append(img_path)

        return {
            "task_id": task_id,
            "status": inner.get("status", "unknown"),
            "progress": inner.get("progress"),
            "images": images if images else None,
            "error": inner.get("error") if inner.get("status") == "failed" else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usage")
async def get_usage(authorization: Optional[str] = Header(None)):
    """获取使用量统计"""
    client_id = get_client_id(authorization)
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{client_id}:{today}"
    used = user_requests.get(key, 0)

    return {
        "today": today,
        "used": used,
        "limit": settings.DAILY_LIMIT,
        "remaining": max(0, settings.DAILY_LIMIT - used)
    }


@app.get("/api/download")
async def download_image_proxy(url: str):
    """代理下载图片，解决跨域问题"""
    from fastapi.responses import Response
    import mimetypes

    try:
        # 如果是本地图片路径（/images/xxx.png），直接从文件系统读取
        if url.startswith("/images/"):
            filename = url.replace("/images/", "")
            filepath = settings.IMAGE_DIR / filename
            if filepath.exists():
                mime_type = mimetypes.guess_type(str(filepath))[0] or "image/png"
                return Response(
                    content=filepath.read_bytes(),
                    media_type=mime_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            else:
                raise HTTPException(status_code=404, detail="Image not found")

        # 如果是外部URL，通过服务器代理下载
        resp = SESSION.get(url, timeout=60)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "image/png")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={"Content-Disposition": "attachment; filename=image.png"}
            )
        else:
            raise HTTPException(status_code=resp.status_code, detail="Failed to download image")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 静态文件服务（图片）
settings.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=settings.IMAGE_DIR), name="images")

# 启动定时清理任务
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_images, "interval", hours=1)
scheduler.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
