"""Example 2: call an OpenAI-compatible chat API with the OpenAI SDK."""

import asyncio

from openai import APIConnectionError, APIStatusError, AsyncOpenAI
from src.core.config_manager import get_config


def _is_placeholder(value: str) -> bool:
    return not value or value.startswith("your_") or "example.com" in value


async def main() -> None:
    config = get_config()
    if _is_placeholder(config.api_key) or _is_placeholder(config.api_base_url):
        print("跳过 OpenAI SDK 示例：未配置有效的 API_BASE_URL 或 API_KEY。")
        return

    client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_base_url)
    try:
        response = await client.chat.completions.create(
            model=config.model_name,
            messages=[{"role": "user", "content": "请用一句话介绍你自己。"}],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.llm_timeout,
        )
    except APIStatusError as exc:
        print(f"OpenAI SDK 示例请求失败：status={exc.status_code}")
        return
    except APIConnectionError as exc:
        print(f"OpenAI SDK 示例连接失败：{type(exc).__name__}")
        return
    finally:
        await client.close()

    content = response.choices[0].message.content or ""
    print(f"OpenAI SDK 示例调用成功：{content}")
    print(f"Token usage：{response.usage if response.usage else '服务未提供'}")


if __name__ == "__main__":
    asyncio.run(main())
