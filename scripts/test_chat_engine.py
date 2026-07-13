"""Smoke test for the Step 6 ChatEngine.

This script calls an external OpenAI-compatible service only when a real
API_BASE_URL and API_KEY are configured in the local, untracked `.env`.
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402
from src.core.chat_engine import (  # noqa: E402
    ChatEngine,
    ChatEngineResult,
    ChatStreamEvent,
)
from src.core.config_manager import get_config  # noqa: E402


def _is_placeholder(value: str) -> bool:
    return not value or value.startswith("your_") or "example.com" in value


def _print_usage(label: str, result: ChatEngineResult | ChatStreamEvent) -> None:
    usage = result.usage
    if usage is None or not usage.provided:
        print(f"{label} Token usage：服务未提供")
        return
    print(
        f"{label} Token usage："
        f"prompt={usage.prompt_tokens}, "
        f"completion={usage.completion_tokens}, "
        f"total={usage.total_tokens}"
    )


async def _run_external_smoke(engine: ChatEngine) -> None:
    print("[1/5] 非流式单轮调用")
    single = await engine.generate([HumanMessage(content="请用一句话回复：你好")])
    print(f"      回复长度：{len(single.content)}")
    _print_usage("      单轮", single)

    print("[2/5] 带消息历史的多轮上下文调用")
    history = [
        HumanMessage(content="我给一个测试变量起名为 project_codename。"),
        AIMessage(content="好的，我记住这个测试变量名。"),
        HumanMessage(content="刚才的测试变量名是什么？"),
    ]
    contextual = await engine.generate(history)
    print(f"      回复长度：{len(contextual.content)}")
    _print_usage("      多轮", contextual)

    print("[3/5] SystemMessage 注入")
    system_result = await engine.generate(
        [
            SystemMessage(content="你必须使用简洁中文回答。"),
            HumanMessage(content="请说明你收到了一条 system message。"),
        ]
    )
    print(f"      回复长度：{len(system_result.content)}")
    _print_usage("      SystemMessage", system_result)

    print("[4/5] 异步流式输出")
    final_event = None
    streamed_text = []
    async for event in engine.stream([HumanMessage(content="请数三个数。")]):
        if event.is_final:
            final_event = event
            continue
        streamed_text.append(event.content)
        print(event.content, end="", flush=True)
    print()
    if final_event is None:
        raise RuntimeError("流式调用未产生最终事件。")
    print(f"      流式回复长度：{len(''.join(streamed_text))}")
    _print_usage("      流式", final_event)

    print("[5/5] 异常传播检查")
    try:
        await engine.generate([])
    except ValueError as exc:
        print(f"      已捕获预期异常：{type(exc).__name__}")
    else:
        raise RuntimeError("空消息列表没有触发预期异常。")


async def main() -> int:
    print("Step 6：ChatEngine 冒烟测试")
    config = get_config()
    engine = ChatEngine(config)
    print(f"配置加载成功，模型：{config.model_name}")
    print("ChatEngine 创建成功。")

    try:
        try:
            await engine.generate([])
        except ValueError as exc:
            print(f"本地异常处理验证通过：{type(exc).__name__}")
        else:
            print("本地异常处理验证失败：空消息列表未抛出异常。")
            return 1

        if _is_placeholder(config.api_key) or _is_placeholder(config.api_base_url):
            print(
                "未配置有效 LLM 环境，跳过外部非流式、历史、SystemMessage 和流式调用。"
            )
            return 0

        await _run_external_smoke(engine)
        print("ChatEngine 外部冒烟测试完成。")
        return 0
    except Exception as exc:
        print(f"ChatEngine 外部冒烟测试失败：{type(exc).__name__}")
        return 1
    finally:
        await engine.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
