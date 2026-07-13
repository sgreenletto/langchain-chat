"""Example 3: call an OpenAI-compatible chat API with LangChain."""

import asyncio

from langchain_core.messages import HumanMessage
from src.core.chat_engine import ChatEngine
from src.core.config_manager import get_config


def _is_placeholder(value: str) -> bool:
    return not value or value.startswith("your_") or "example.com" in value


async def main() -> None:
    config = get_config()
    if _is_placeholder(config.api_key) or _is_placeholder(config.api_base_url):
        print("跳过 LangChain 示例：未配置有效的 API_BASE_URL 或 API_KEY。")
        return

    engine = ChatEngine(config)
    try:
        result = await engine.generate([HumanMessage(content="请用一句话介绍你自己。")])
    except Exception as exc:
        print(f"LangChain 示例请求失败：{type(exc).__name__}")
        return
    finally:
        await engine.close()

    print(f"LangChain 示例调用成功：{result.content}")
    if result.usage.provided:
        print(
            "Token usage："
            f"prompt={result.prompt_tokens}, "
            f"completion={result.completion_tokens}, "
            f"total={result.total_tokens}"
        )
    else:
        print("Token usage：服务未提供")


if __name__ == "__main__":
    asyncio.run(main())
