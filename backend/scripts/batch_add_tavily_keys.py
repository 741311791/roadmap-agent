#!/usr/bin/env python3
"""
批量添加 Tavily API Keys 脚本

功能：
- 调用管理员接口批量添加 Tavily API Keys
- 支持从命令行或环境变量读取认证信息
- 显示详细的添加结果

使用方法：
    # 方式1: 使用环境变量
    export API_BASE_URL="http://localhost:8000"
    export ADMIN_EMAIL="admin@example.com"
    export ADMIN_PASSWORD="your_password"
    python scripts/batch_add_tavily_keys.py

    # 方式2: 使用命令行参数
    python scripts/batch_add_tavily_keys.py \
        --base-url http://localhost:8000 \
        --email admin@example.com \
        --password your_password
"""

import asyncio
import os
import sys
import argparse
from typing import List, Dict
import httpx
import structlog

# 配置日志
logger = structlog.get_logger()

# Tavily API Keys 列表
TAVILY_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]

# 默认配额
DEFAULT_PLAN_LIMIT = 1000


async def login(base_url: str, email: str, password: str) -> str:
    """
    登录获取 JWT Token
    
    Args:
        base_url: API 基础 URL
        email: 管理员邮箱
        password: 管理员密码
        
    Returns:
        JWT Token
        
    Raises:
        Exception: 登录失败
    """
    logger.info("开始登录", email=email)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/api/v1/auth/jwt/login",
                data={
                    "username": email,
                    "password": password,
                },
            )
            
            response.raise_for_status()
            data = response.json()
            
            token = data.get("access_token")
            if not token:
                raise ValueError("响应中未找到 access_token")
            
            logger.info("登录成功")
            return token
            
        except httpx.HTTPStatusError as e:
            logger.error("登录失败", status_code=e.response.status_code, detail=e.response.text)
            raise Exception(f"登录失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error("登录异常", error=str(e))
            raise


async def verify_superuser(base_url: str, token: str) -> dict:
    """
    验证用户是否为超级管理员
    
    Args:
        base_url: API 基础 URL
        token: JWT Token
        
    Returns:
        用户信息
        
    Raises:
        Exception: 验证失败或用户不是超级管理员
    """
    logger.info("验证超级管理员权限")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            response.raise_for_status()
            user_data = response.json()
            
            # 检查是否为超级管理员
            is_superuser = user_data.get("is_superuser", False)
            email = user_data.get("email", "unknown")
            
            if not is_superuser:
                logger.error(
                    "用户不是超级管理员",
                    email=email,
                    is_superuser=is_superuser
                )
                raise Exception(
                    f"用户 {email} 不是超级管理员，无法执行此操作。"
                    f"请使用超级管理员账户登录。"
                )
            
            logger.info(
                "超级管理员权限验证通过",
                email=email,
                is_superuser=is_superuser
            )
            return user_data
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "验证失败",
                status_code=e.response.status_code,
                detail=e.response.text
            )
            raise Exception(
                f"验证失败: HTTP {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error("验证异常", error=str(e))
            raise


async def batch_add_tavily_keys(
    base_url: str,
    token: str,
    keys: List[str],
    plan_limit: int = DEFAULT_PLAN_LIMIT
) -> Dict:
    """
    批量添加 Tavily API Keys
    
    Args:
        base_url: API 基础 URL
        token: JWT Token
        keys: API Key 列表
        plan_limit: 每个 Key 的配额限制
        
    Returns:
        批量添加结果
        
    Raises:
        Exception: 添加失败
    """
    logger.info("开始批量添加 Tavily Keys", count=len(keys), plan_limit=plan_limit)
    
    # 构建请求数据
    request_data = {
        "keys": [
            {"api_key": key, "plan_limit": plan_limit}
            for key in keys
        ]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{base_url}/api/v1/admin/tavily-keys/batch",
                json=request_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                "批量添加完成",
                success=result.get("data", {}).get("success"),
                failed=result.get("data", {}).get("failed"),
            )
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "批量添加失败",
                status_code=e.response.status_code,
                detail=e.response.text
            )
            raise Exception(
                f"批量添加失败: HTTP {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error("批量添加异常", error=str(e))
            raise


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="批量添加 Tavily API Keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用环境变量
    export API_BASE_URL="http://localhost:8000"
    export ADMIN_EMAIL="admin@example.com"
    export ADMIN_PASSWORD="your_password"
    python scripts/batch_add_tavily_keys.py

    # 使用命令行参数
    python scripts/batch_add_tavily_keys.py \\
        --base-url http://localhost:8000 \\
        --email admin@example.com \\
        --password your_password \\
        --plan-limit 1000
        """
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="API 基础 URL (默认: http://localhost:8000)",
    )
    
    parser.add_argument(
        "--email",
        type=str,
        default=os.getenv("ADMIN_EMAIL"),
        help="管理员邮箱 (可通过环境变量 ADMIN_EMAIL 设置)",
    )
    
    parser.add_argument(
        "--password",
        type=str,
        default=os.getenv("ADMIN_PASSWORD"),
        help="管理员密码 (可通过环境变量 ADMIN_PASSWORD 设置)",
    )
    
    parser.add_argument(
        "--plan-limit",
        type=int,
        default=DEFAULT_PLAN_LIMIT,
        help=f"每个 Key 的配额限制 (默认: {DEFAULT_PLAN_LIMIT})",
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()
    
    # 验证必需参数
    if not args.email:
        logger.error("缺少管理员邮箱，请通过 --email 或环境变量 ADMIN_EMAIL 设置")
        sys.exit(1)
    
    if not args.password:
        logger.error("缺少管理员密码，请通过 --password 或环境变量 ADMIN_PASSWORD 设置")
        sys.exit(1)
    
    try:
        # 步骤1: 登录获取 Token
        logger.info("=" * 60)
        logger.info("步骤 1: 登录")
        logger.info("=" * 60)
        token = await login(args.base_url, args.email, args.password)
        
        # 步骤2: 验证超级管理员权限
        logger.info("")
        logger.info("=" * 60)
        logger.info("步骤 2: 验证超级管理员权限")
        logger.info("=" * 60)
        user_info = await verify_superuser(args.base_url, token)
        
        # 步骤3: 批量添加 Keys
        logger.info("")
        logger.info("=" * 60)
        logger.info("步骤 3: 批量添加 Tavily Keys")
        logger.info("=" * 60)
        logger.info(f"待添加 Keys 数量: {len(TAVILY_KEYS)}")
        logger.info(f"每个 Key 配额: {args.plan_limit}")
        logger.info("")
        
        result = await batch_add_tavily_keys(
            args.base_url,
            token,
            TAVILY_KEYS,
            args.plan_limit
        )
        
        # 步骤4: 显示结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("添加结果")
        logger.info("=" * 60)
        
        data = result.get("data", {})
        success_count = data.get("success", 0)
        failed_count = data.get("failed", 0)
        errors = data.get("errors", [])
        
        logger.info(f"✅ 成功: {success_count}")
        logger.info(f"❌ 失败: {failed_count}")
        
        if errors:
            logger.info("")
            logger.info("失败详情:")
            for error in errors:
                api_key = error.get("api_key", "unknown")
                error_msg = error.get("error", "unknown error")
                logger.warning(f"  - {api_key}: {error_msg}")
        
        logger.info("=" * 60)
        
        # 返回结果
        if failed_count > 0:
            logger.warning(f"部分 Keys 添加失败 ({failed_count}/{len(TAVILY_KEYS)})")
            sys.exit(1)
        else:
            logger.info("所有 Keys 添加成功！")
            sys.exit(0)
            
    except Exception as e:
        logger.error("执行失败", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

