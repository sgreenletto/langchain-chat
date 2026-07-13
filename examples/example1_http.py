"""Example 1: call an OpenAI-compatible chat API with raw HTTP."""

import asyncio

import httpx
from src.core.config_manager import get_config


def _is_placeholder(value: str) -> bool:
    return not value or value.startswith("your_") or "example.com" in value


async def main() -> None:
    config = get_config()
    if _is_placeholder(config.api_key) or _is_placeholder(config.api_base_url):
        print("跳过 HTTP 示例：未配置有效的 API_BASE_URL 或 API_KEY。")
        return

    endpoint = f"{config.api_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": config.model_name,
        "messages": [{"role": "user", "content": "请用一句话介绍你自己。"}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": False,
    }
    headers = {"Authorization": "Bearer ***", "Content-Type": "application/json"}
    request_headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=config.llm_timeout) as client:
            response = await client.post(
                endpoint,
                headers=request_headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"HTTP 示例请求失败：status={exc.response.status_code}")
        return
    except httpx.HTTPError as exc:
        print(f"HTTP 示例请求失败：{type(exc).__name__}")
        return

    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage")
    print(f"HTTP 示例调用成功：{content}")
    print(f"请求头示例已脱敏：{headers}")
    print(f"Token usage：{usage if usage else '服务未提供'}")


if __name__ == "__main__":
    asyncio.run(main())
