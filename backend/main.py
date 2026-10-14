import os
import json
import base64
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

import requests
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings

app = FastAPI(title="ImageGen Proxy API", version="3.0.0")

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

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer
security = HTTPBearer(auto_error=False)


# ==================== 数据库 ====================

def init_database():
    """初始化数据库"""
    settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(settings.DATABASE_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                daily_limit INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                prompt TEXT,
                model TEXT,
                size TEXT,
                resolution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()


@contextmanager
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(settings.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    """通过ID获取用户"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[dict]:
    """通过用户名获取用户"""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def create_user(username: str, email: Optional[str], password: str, is_admin: bool = False) -> dict:
    """创建用户"""
    password_hash = pwd_context.hash(password)
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, is_admin)
        )
        conn.commit()
        return get_user_by_id(cursor.lastrowid)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, username: str, is_admin: bool) -> str:
    """创建JWT令牌"""
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "is_admin": is_admin,
        "exp": expire
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """获取当前用户"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[dict]:
    """获取可选用户（未登录返回None）"""
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    
    return get_user_by_id(int(payload["sub"]))


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


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=20)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class UpdateProfileRequest(BaseModel):
    """更新资料请求"""
    email: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None


# ==================== 工具函数 ====================

def image_to_data_url(path_or_base64: str) -> str:
    """将图片路径或base64转换为data URL"""
    if path_or_base64.startswith("data:"):
        return path_or_base64
    if path_or_base64.startswith("http"):
        return path_or_base64
    return f"data:image/png;base64,{path_or_base64}"


def check_rate_limit(user_id: int) -> bool:
    """检查请求频率限制"""
    user = get_user_by_id(user_id)
    if not user:
        return False
    
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM images WHERE user_id = ? AND DATE(created_at) = ?",
            (user_id, today)
        ).fetchone()
        count = row["cnt"]
    
    return count < user.get("daily_limit", settings.DAILY_LIMIT)


def get_today_usage(user_id: int) -> dict:
    """获取今日使用量"""
    user = get_user_by_id(user_id)
    if not user:
        return {"used": 0, "limit": settings.DAILY_LIMIT, "remaining": settings.DAILY_LIMIT}
    
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM images WHERE user_id = ? AND DATE(created_at) = ?",
            (user_id, today)
        ).fetchone()
        count = row["cnt"]
    
    limit = user.get("daily_limit", settings.DAILY_LIMIT)
    return {
        "today": today,
        "used": count,
        "limit": limit,
        "remaining": max(0, limit - count)
    }


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


def save_image(url_or_b64, filename_prefix: str, user_id: int, prompt: str = "", model: str = "", size: str = "", resolution: str = "") -> Optional[str]:
    """保存图片并返回URL"""
    settings.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{filename_prefix}.png"
    filepath = settings.IMAGE_DIR / filename

    if isinstance(url_or_b64, tuple) and url_or_b64[0] == "b64":
        filepath.write_bytes(base64.b64decode(url_or_b64[1]))
    elif isinstance(url_or_b64, str):
        if url_or_b64.startswith("data:"):
            header, data = url_or_b64.split(",", 1)
            filepath.write_bytes(base64.b64decode(data))
        else:
            if not download_image(url_or_b64, filepath):
                return None
    else:
        return None

    # 记录到数据库
    with get_db() as conn:
        conn.execute(
            "INSERT INTO images (user_id, filename, prompt, model, size, resolution) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, filename, prompt, model, size, resolution)
        )
        conn.commit()

    return f"/images/{filename}"


# ==================== API路由 ====================

@app.get("/")
async def root():
    return {"message": "ImageGen Proxy API", "version": "3.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ==================== 认证接口 ====================

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """用户注册"""
    # 检查用户名是否已存在
    if get_user_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # 第一个用户自动成为管理员
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        is_first = row["cnt"] == 0
    
    user = create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        is_admin=is_first
    )
    
    token = create_access_token(user["id"], user["username"], user["is_admin"])
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    }


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """用户登录"""
    user = get_user_by_username(request.username)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 更新最后登录时间
    with get_db() as conn:
        conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
        conn.commit()
    
    token = create_access_token(user["id"], user["username"], user["is_admin"])
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_admin": user["is_admin"],
        "daily_limit": user.get("daily_limit", settings.DAILY_LIMIT)
    }


@app.put("/api/auth/profile")
async def update_profile(request: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """更新用户资料"""
    with get_db() as conn:
        if request.email:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (request.email, user["id"]))
        
        if request.new_password:
            if not request.old_password or not verify_password(request.old_password, user["password_hash"]):
                raise HTTPException(status_code=400, detail="Invalid old password")
            new_hash = pwd_context.hash(request.new_password)
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
        
        conn.commit()
    
    return {"success": True}


# ==================== 管理员接口 ====================

@app.get("/api/admin/users")
async def list_users(user: dict = Depends(get_current_user)):
    """获取所有用户列表（管理员）"""
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin only")
    
    with get_db() as conn:
        rows = conn.execute("SELECT id, username, email, is_admin, daily_limit, created_at, last_login FROM users").fetchall()
    
    return {
        "users": [dict(row) for row in rows]
    }


@app.put("/api/admin/users/{user_id}/limit")
async def set_user_limit(user_id: int, limit: int, user: dict = Depends(get_current_user)):
    """设置用户每日限额（管理员）"""
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin only")
    
    with get_db() as conn:
        conn.execute("UPDATE users SET daily_limit = ? WHERE id = ?", (limit, user_id))
        conn.commit()
    
    return {"success": True}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, user: dict = Depends(get_current_user)):
    """删除用户（管理员）"""
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin only")
    
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    with get_db() as conn:
        conn.execute("DELETE FROM images WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    
    return {"success": True}


# ==================== 图片接口 ====================

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
    user: dict = Depends(get_current_user)
):
    """文生图接口"""
    if not settings.APIMART_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    # 频率限制
    if not check_rate_limit(user["id"]):
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded ({user.get('daily_limit', settings.DAILY_LIMIT)} requests/day)"
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
            img_path = save_image(
                url_or_b64, str(i), user["id"],
                prompt=request.prompt, model="gpt-image-2",
                size=request.size, resolution=request.resolution
            )
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
    user: dict = Depends(get_current_user)
):
    """图生图接口"""
    if not settings.APIMART_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    # 频率限制
    if not check_rate_limit(user["id"]):
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded ({user.get('daily_limit', settings.DAILY_LIMIT)} requests/day)"
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
            img_path = save_image(
                url_or_b64, str(i), user["id"],
                prompt=request.prompt, model="gpt-image-2",
                size=request.size, resolution=request.resolution
            )
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

        # 提取图片URL（需要用户ID才能保存）
        images = []
        if inner.get("status") == "completed":
            urls = extract_urls(inner)
            # 这里无法获取用户ID，返回URL让用户后续处理
            for url_or_b64 in urls:
                if isinstance(url_or_b64, tuple):
                    images.append(f"data:image/png;base64,{url_or_b64[1][:50]}...")
                else:
                    images.append(url_or_b64)

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
async def get_usage(user: dict = Depends(get_current_user)):
    """获取使用量统计"""
    return get_today_usage(user["id"])


@app.get("/api/history")
async def get_history(user: dict = Depends(get_current_user), limit: int = Query(20, ge=1, le=100)):
    """获取生成历史"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM images WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user["id"], limit)
        ).fetchall()
    
    return {
        "images": [dict(row) for row in rows]
    }


@app.get("/api/download")
async def download_image_proxy(url: str, user: dict = Depends(get_current_user)):
    """代理下载图片，解决跨域问题"""
    import mimetypes

    try:
        # 如果是本地图片路径（/images/xxx.png），验证所有权
        if url.startswith("/images/"):
            filename = url.replace("/images/", "")
            filepath = settings.IMAGE_DIR / filename
            
            # 验证图片所有权
            with get_db() as conn:
                row = conn.execute(
                    "SELECT * FROM images WHERE filename = ? AND user_id = ?",
                    (filename, user["id"])
                ).fetchone()
            
            if not row:
                # 管理员可以查看所有图片
                if not user["is_admin"]:
                    raise HTTPException(status_code=403, detail="Access denied")
            
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

# 初始化数据库
init_database()

# 启动定时清理任务
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_images, "interval", hours=1)
scheduler.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
