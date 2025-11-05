"""
Stream Helper - 通用Agent Stream包装器
支持extended thinking和模型切换
"""

import json
from typing import AsyncGenerator, Dict, Any
from .bedrock_adapter import BedrockLLM


def stream_agent_with_thinking(
    prompt: str,
    system_prompt: str = None,
    model: str = "haiku",
    max_tokens: int = 16000,
    enable_thinking: bool = True
):
    """
    通用agent stream生成器（支持extended thinking）

    Args:
        prompt: 用户prompt
        system_prompt: 系统prompt
        model: 模型名称（haiku, haiku-3.5, sonnet等）
        max_tokens: 最大token数
        enable_thinking: 是否启用extended thinking

    Yields:
        SSE格式的消息: "data: {JSON}\\n\\n"

    消息类型:
        - {"type": "thinking_start"} - Thinking开始
        - {"type": "thinking", "content": "..."} - Thinking内容
        - {"type": "thinking_end"} - Thinking结束
        - {"type": "chunk", "content": "..."} - 正常文本chunk
        - {"type": "complete", "detailed": "..."} - 完成
        - {"error": "..."} - 错误

    Usage:
        async for message in stream_agent_with_thinking(
            prompt="分析玩家数据",
            model="haiku",
            enable_thinking=True
        ):
            yield message
    """
    try:
        # 初始化LLM
        llm = BedrockLLM(model=model)

        # 调试信息
        print(f"🔍 Stream starting: model={model}, prompt_len={len(prompt)}, system_len={len(system_prompt) if system_prompt else 0}")
        print(f"   enable_thinking={enable_thinking}, max_tokens={max_tokens}")

        # Stream生成detailed report
        detailed_chunks = []
        thinking_chunks = []

        chunk_count = 0
        print(f"🔍 About to call llm.generate_stream...")
        stream_generator = llm.generate_stream(
            prompt=prompt,
            system=system_prompt,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking
        )
        print(f"🔍 Stream generator created: {type(stream_generator)}")
        print(f"🔍 Starting iteration...")

        try:
            for chunk in stream_generator:
                chunk_count += 1

                # 处理thinking标记
                if chunk == '__THINKING_START__':
                    if chunk_count <= 3:
                        print(f"   Chunk {chunk_count}: [THINKING_START]")
                    yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                    continue
                elif chunk == '__THINKING_END__':
                    if chunk_count <= 3:
                        print(f"   Chunk {chunk_count}: [THINKING_END]")
                    yield f"data: {json.dumps({'type': 'thinking_end'})}\n\n"
                    continue
                elif chunk.startswith('__THINKING__'):
                    # Thinking内容
                    thinking_text = chunk[12:]  # 去掉__THINKING__前缀
                    thinking_chunks.append(thinking_text)
                    if chunk_count <= 3:
                        print(f"   Chunk {chunk_count}: [THINKING] {thinking_text[:50]}")
                    yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_text})}\n\n"
                    continue

                # 正常文本内容
                detailed_chunks.append(chunk)
                if chunk_count <= 3:
                    print(f"   Chunk {chunk_count}: {chunk[:50]}")
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            print(f"✅ Stream complete: {chunk_count} chunks received")
        except Exception as e:
            import traceback
            print(f"❌ Stream iteration error: {traceback.format_exc()}")
            raise
        detailed = "".join(detailed_chunks)

        # 返回完整结果
        yield f"data: {json.dumps({'type': 'complete', 'detailed': detailed})}\n\n"

    except Exception as e:
        import traceback
        error_msg = f"Stream error: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
