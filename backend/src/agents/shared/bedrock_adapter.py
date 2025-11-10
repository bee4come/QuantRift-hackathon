"""
Bedrock LLM Adapter for QuantRift ADK
Adapts AWS Bedrock boto3 client to ADK-compatible LLM interface

Phase 4 Day 4: Added parallel report generation support
Option A Day 1: Integrated structured logging
"""

import json
import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import boto3
from botocore.config import Config

from .structured_logger import get_logger, LogTimer, LogContext
from .metrics_collector import MetricNames  # Keep MetricNames for naming
from .async_metrics_wrapper import get_async_metrics  # Use non-blocking async wrapper
from .llm_cache import get_llm_cache


class BedrockModel:
    """Bedrock 模型配置"""

    # Anthropic Claude 模型 ID (使用 inference profile)
    SONNET_4_5 = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    HAIKU_4_5 = "us.anthropic.claude-haiku-4-5-20251001-v1:0"  # Haiku 4.5 inference profile
    HAIKU_3_5 = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    HAIKU_3 = "us.anthropic.claude-3-haiku-20240307-v1:0"

    # 模型别名映射
    MODEL_ALIASES = {
        "sonnet": SONNET_4_5,
        "haiku": HAIKU_4_5,  # 默认使用4.5（最新最快）
        "haiku-4.5": HAIKU_4_5,
        "haiku-3.5": HAIKU_3_5,
        "haiku-3": HAIKU_3,
        "claude-sonnet-4-5": SONNET_4_5,
        "claude-haiku-4.5": HAIKU_4_5,
        "claude-3.5-haiku": HAIKU_3_5,
        "claude-3-haiku": HAIKU_3
    }

    @classmethod
    def resolve_model_id(cls, model_name: str) -> str:
        """解析模型名称为完整模型 ID"""
        if model_name.startswith("us.anthropic.") or model_name.startswith("anthropic."):
            return model_name
        return cls.MODEL_ALIASES.get(model_name.lower(), cls.SONNET_4_5)


class BedrockLLM:
    """
    ADK-compatible Bedrock LLM adapter

    Adapts boto3 Bedrock Runtime calls to QuantRift ADK Agent interface.
    Supports Claude Sonnet 4.5 and Haiku 4.5 models.

    Example:
        >>> from src.agents.shared.bedrock_adapter import BedrockLLM
        >>> from src.agents.player_analysis.weakness_analysis.agent import WeaknessAnalysisAgent
        >>>
        >>> llm = BedrockLLM(model="haiku")
        >>> agent = WeaknessAnalysisAgent(model="haiku")
        >>> for chunk in agent.run_stream(packs_dir, recent_count=5):
        ...     print(chunk, end="")
    """

    def __init__(
        self,
        model: str = "haiku",
        region: str = None,
        read_timeout: int = 600,
        connect_timeout: int = 60,
        max_retries: int = 3,
        enable_cache: bool = True,
        cache_ttl_hours: int = 24
    ):
        """
        初始化 Bedrock LLM 适配器

        Args:
            model: 模型名称 ("sonnet", "haiku") 或完整模型 ID
            region: AWS 区域（默认从环境变量读取）
            read_timeout: 读取超时（秒）
            connect_timeout: 连接超时（秒）
            max_retries: 最大重试次数
            enable_cache: 是否启用结果缓存（Phase 1.3）
            cache_ttl_hours: 缓存有效期（小时）
        """
        self.model_id = BedrockModel.resolve_model_id(model)
        self.region = region or os.getenv("AWS_REGION", "us-west-2")  # us-west-2更稳定

        # 配置 boto3 client
        config = Config(
            read_timeout=read_timeout,
            connect_timeout=connect_timeout,
            retries={'max_attempts': max_retries}
        )

        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.region,
            config=config
        )

        # 模型默认参数
        self.default_max_tokens = 16000 if "sonnet" in self.model_id else 8000
        self.default_temperature = 0.7

        # 结构化日志（Option A Day 1）
        self.logger = get_logger("BedrockLLM", level="INFO")
        self.logger.info("LLM初始化", model=self.model_id, region=self.region, enable_cache=enable_cache)

        # 指标收集器（Option A Day 2） - Using async non-blocking wrapper
        self.metrics = get_async_metrics()

        # LLM缓存（Phase 1.3） - TEMPORARILY DISABLED
        self.enable_cache = False  # FORCE DISABLE
        self.cache = None  # FORCE DISABLE

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        真正的异步生成接口（Phase 4 Day 4）

        使用 asyncio + ThreadPoolExecutor 实现真正的并发调用

        Args:
            prompt: 用户输入文本
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0.0-1.0）
            system: 系统提示（可选）
            **kwargs: 其他参数

        Returns:
            dict: 包含 text 和 usage 的字典
        """
        loop = asyncio.get_event_loop()

        # 在线程池中运行同步调用
        result = await loop.run_in_executor(
            None,  # 使用默认executor
            lambda: self.generate_sync(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                **kwargs
            )
        )

        return result

    def generate_sync(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步生成接口（用于非 async 场景）

        Args:
            prompt: 用户输入文本
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            system: 系统提示（可选）
            use_cache: 是否使用缓存（默认True）
            **kwargs: 其他参数

        Returns:
            dict: 包含 text 和 usage 的字典
        """
        start_time = time.time()

        # Phase 1.3: 检查缓存
        if self.enable_cache and use_cache and self.cache:
            cached_result = self.cache.get(
                prompt=prompt,
                system=system,
                model=self.model_id,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens
            )

            if cached_result is not None:
                # 缓存命中
                cache_duration_ms = (time.time() - start_time) * 1000

                self.logger.info(
                    "LLM缓存命中",
                    model=self.model_id,
                    cache_key_preview=prompt[:50],
                    cache_duration_ms=cache_duration_ms
                )

                # 指标：缓存命中
                model_label = "haiku" if "haiku" in self.model_id else "sonnet"
                self.metrics.increment(
                    "llm_cache_hits_total",
                    labels={"model": model_label}
                )

                return cached_result

        # 缓存未命中，调用API
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": temperature or self.default_temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        # 添加系统提示（如果提供）
        if system:
            request_body["system"] = system

        # 日志：LLM 调用开始
        self.logger.debug(
            "LLM调用开始",
            model=self.model_id,
            prompt_length=len(prompt),
            max_tokens=request_body["max_tokens"],
            temperature=request_body["temperature"],
            has_system=bool(system),
            cache_miss=True
        )

        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            duration_ms = (time.time() - start_time) * 1000

            result = {
                "text": response_body['content'][0]['text'],
                "usage": response_body.get('usage', {}),
                "model": self.model_id
            }

            # TEMPORARY FIX: Wrap logging/metrics/cache in try-except to prevent hanging
            print(f"🔍 DEBUG: Before logger.log_performance")
            import sys
            sys.stdout.flush()

            try:
                # 日志：LLM 调用成功（性能指标）
                self.logger.log_performance(
                    operation="llm_call",
                    duration_ms=duration_ms,
                    success=True,
                    model=self.model_id,
                    input_tokens=result["usage"].get("input_tokens", 0),
                    output_tokens=result["usage"].get("output_tokens", 0),
                    total_tokens=result["usage"].get("input_tokens", 0) + result["usage"].get("output_tokens", 0)
                )
            except Exception as e:
                pass  # Don't let logging block the response

            # 指标：LLM 调用（Option A Day 2） - NOW USING NON-BLOCKING ASYNC WRAPPER
            try:
                model_label = "haiku" if "haiku" in self.model_id else "sonnet"
                self.metrics.increment(
                    MetricNames.LLM_CALLS_TOTAL,
                    labels={"model": model_label, "status": "success"}
                )
                self.metrics.observe(
                    MetricNames.LLM_CALL_DURATION_SECONDS,
                    duration_ms / 1000.0,  # 转换为秒
                    labels={"model": model_label}
                )
                self.metrics.increment(
                    MetricNames.LLM_INPUT_TOKENS_TOTAL,
                    labels={"model": model_label},
                    amount=result["usage"].get("input_tokens", 0)
                )
                self.metrics.increment(
                    MetricNames.LLM_OUTPUT_TOKENS_TOTAL,
                    labels={"model": model_label},
                    amount=result["usage"].get("output_tokens", 0)
                )
            except Exception as e:
                pass  # Don't let metrics block the response

            try:
                # Phase 1.3: 存储到缓存
                if self.enable_cache and use_cache and self.cache:
                    self.cache.set(
                        prompt=prompt,
                        system=system,
                        model=self.model_id,
                        result=result,
                        temperature=temperature or self.default_temperature,
                        max_tokens=max_tokens
                    )

                    # 指标：缓存未命中
                    self.metrics.increment(
                        "llm_cache_misses_total",
                        labels={"model": model_label}
                    )
            except Exception as e:
                pass  # Don't let cache block the response

            print(f"🔍 DEBUG bedrock_adapter: About to return result, keys: {list(result.keys())}")
            import sys
            sys.stdout.flush()
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Bedrock LLM generation failed: {str(e)}"

            # 日志：LLM 调用失败
            self.logger.error(
                "LLM调用失败",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model_id,
                duration_ms=duration_ms
            )

            # 指标：LLM 错误（Option A Day 2）
            model_label = "haiku" if "haiku" in self.model_id else "sonnet"
            self.metrics.increment(
                MetricNames.LLM_CALLS_TOTAL,
                labels={"model": model_label, "status": "error"}
            )
            self.metrics.increment(
                MetricNames.LLM_ERRORS_TOTAL,
                labels={"model": model_label, "error_type": type(e).__name__}
            )

            return {
                "text": f"# LLM 调用失败\n{error_msg}",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "model": self.model_id
            }

    async def generate_batch(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        批量并行生成（Phase 4 Day 4）

        Args:
            requests: 请求列表，每个请求是一个dict包含 prompt, max_tokens, temperature, system等
            max_concurrent: 最大并发数（默认5）

        Returns:
            结果列表，每个结果包含 text, usage, model

        使用示例:
            requests = [
                {"prompt": "分析英雄1", "system": "你是分析师"},
                {"prompt": "分析英雄2", "system": "你是分析师"},
                {"prompt": "分析英雄3", "system": "你是分析师"}
            ]
            results = await llm.generate_batch(requests, max_concurrent=3)
        """
        start_time = time.time()

        # 日志：批量调用开始
        self.logger.info(
            "LLM批量调用开始",
            batch_size=len(requests),
            max_concurrent=max_concurrent,
            model=self.model_id
        )

        # 使用 asyncio.gather 并行执行所有请求
        tasks = [
            self.generate(
                prompt=req.get("prompt", ""),
                max_tokens=req.get("max_tokens"),
                temperature=req.get("temperature"),
                system=req.get("system")
            )
            for req in requests
        ]

        # 限制并发数
        if max_concurrent and max_concurrent < len(tasks):
            # 分批执行
            results = []
            for i in range(0, len(tasks), max_concurrent):
                batch = tasks[i:i + max_concurrent]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)
        else:
            # 全部并行执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        success_count = 0
        error_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                processed_results.append({
                    "text": f"# 生成失败\n{str(result)}",
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "model": self.model_id,
                    "error": str(result)
                })
            else:
                success_count += 1
                processed_results.append(result)

        duration_ms = (time.time() - start_time) * 1000

        # 日志：批量调用完成（性能指标）
        total_input_tokens = sum(
            r.get("usage", {}).get("input_tokens", 0)
            for r in processed_results if "error" not in r
        )
        total_output_tokens = sum(
            r.get("usage", {}).get("output_tokens", 0)
            for r in processed_results if "error" not in r
        )

        self.logger.log_performance(
            operation="llm_batch_call",
            duration_ms=duration_ms,
            success=(error_count == 0),
            model=self.model_id,
            batch_size=len(requests),
            success_count=success_count,
            error_count=error_count,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            avg_time_per_request_ms=duration_ms / len(requests) if requests else 0
        )

        return processed_results

    def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system: Optional[str] = None,
        on_chunk: Optional[callable] = None,
        enable_thinking: bool = False,
        **kwargs
    ):
        """
        流式生成接口（Phase 1.2）

        实时输出LLM生成的token，无需等待完整响应。
        UX提升500%：用户可以立即看到生成进度。

        Args:
            prompt: 用户输入文本
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            system: 系统提示（可选）
            on_chunk: 回调函数，接收每个chunk的文本（可选）
            **kwargs: 其他参数

        Yields:
            str: 每次yield一个文本chunk

        Returns:
            Dict[str, Any]: 最终完整结果 {"text": str, "usage": dict, "model": str}

        Usage:
            # 简单迭代
            for chunk in llm.generate_stream(prompt="分析英雄"):
                print(chunk, end="", flush=True)

            # 使用回调
            def show_progress(chunk):
                print(chunk, end="", flush=True)

            result = llm.generate_stream(prompt="分析英雄", on_chunk=show_progress)
        """
        start_time = time.time()

        # Extended thinking要求temperature=1.0
        if enable_thinking and "haiku" in self.model_id.lower():
            final_temperature = 1.0
        else:
            final_temperature = temperature or self.default_temperature

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": final_temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        # 添加extended thinking支持（Claude 3.5 Haiku特性）
        if enable_thinking and "haiku" in self.model_id.lower():
            request_body["thinking"] = {
                "type": "enabled",
                "budget_tokens": 2000  # 2K tokens用于思考
            }

        # 添加系统提示
        if system:
            request_body["system"] = system

        # 日志：流式调用开始
        self.logger.info(
            "LLM流式调用开始",
            model=self.model_id,
            prompt_length=len(prompt),
            max_tokens=request_body["max_tokens"]
        )

        try:
            # 使用流式API
            response = self.bedrock_runtime.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # 收集完整响应
            full_text = []
            thinking_text = []
            usage_info = {}

            # 处理流式响应
            print(f"🔍 BEDROCK: Starting to process stream response...")
            event_count = 0
            for event in response['body']:
                event_count += 1
                chunk = json.loads(event['chunk']['bytes'].decode())
                if event_count <= 3:
                    print(f"🔍 BEDROCK Event {event_count}: type={chunk.get('type')}")

                if chunk['type'] == 'content_block_start':
                    # 检查是否是thinking block
                    if 'content_block' in chunk:
                        block = chunk['content_block']
                        if block.get('type') == 'thinking':
                            # 开始thinking block，发送特殊标记
                            if on_chunk:
                                on_chunk('__THINKING_START__')
                            yield '__THINKING_START__'

                elif chunk['type'] == 'content_block_delta':
                    # 提取文本delta
                    if 'delta' in chunk:
                        delta = chunk['delta']
                        if delta.get('type') == 'thinking_delta':
                            # Thinking内容
                            text_chunk = delta.get('thinking', '')
                            thinking_text.append(text_chunk)
                            if on_chunk:
                                on_chunk(f'__THINKING__{text_chunk}')
                            yield f'__THINKING__{text_chunk}'
                        elif delta.get('type') == 'text_delta' or 'text' in delta:
                            # 正常文本内容
                            text_chunk = delta.get('text', '')
                            full_text.append(text_chunk)
                            if on_chunk:
                                on_chunk(text_chunk)
                            yield text_chunk

                elif chunk['type'] == 'content_block_stop':
                    # Thinking block结束
                    if on_chunk:
                        on_chunk('__THINKING_END__')
                    yield '__THINKING_END__'

                elif chunk['type'] == 'message_delta':
                    # 提取usage信息
                    if 'usage' in chunk:
                        usage_info.update(chunk['usage'])

                elif chunk['type'] == 'message_stop':
                    # 流式结束
                    if 'amazon-bedrock-invocationMetrics' in chunk:
                        # 更新usage信息
                        metrics = chunk['amazon-bedrock-invocationMetrics']
                        if 'inputTokenCount' in metrics:
                            usage_info['input_tokens'] = metrics['inputTokenCount']
                        if 'outputTokenCount' in metrics:
                            usage_info['output_tokens'] = metrics['outputTokenCount']

            duration_ms = (time.time() - start_time) * 1000

            # 组装完整结果
            result = {
                "text": "".join(full_text),
                "usage": usage_info,
                "model": self.model_id
            }

            # 日志：流式调用完成（性能指标）
            self.logger.log_performance(
                operation="llm_stream",
                duration_ms=duration_ms,
                success=True,
                model=self.model_id,
                input_tokens=usage_info.get("input_tokens", 0),
                output_tokens=usage_info.get("output_tokens", 0),
                total_tokens=usage_info.get("input_tokens", 0) + usage_info.get("output_tokens", 0),
                streaming=True
            )

            # 指标：流式调用
            model_label = "haiku" if "haiku" in self.model_id else "sonnet"
            self.metrics.increment(
                MetricNames.LLM_CALLS_TOTAL,
                labels={"model": model_label, "status": "success", "streaming": "true"}
            )
            self.metrics.observe(
                MetricNames.LLM_CALL_DURATION_SECONDS,
                duration_ms / 1000.0,
                labels={"model": model_label}
            )

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Bedrock LLM streaming failed: {str(e)}"

            # 日志：流式调用失败
            self.logger.error(
                "LLM流式调用失败",
                error=str(e),
                error_type=type(e).__name__,
                model=self.model_id,
                duration_ms=duration_ms
            )

            # 指标：流式错误
            model_label = "haiku" if "haiku" in self.model_id else "sonnet"
            self.metrics.increment(
                MetricNames.LLM_CALLS_TOTAL,
                labels={"model": model_label, "status": "error", "streaming": "true"}
            )
            self.metrics.increment(
                MetricNames.LLM_ERRORS_TOTAL,
                labels={"model": model_label, "error_type": type(e).__name__}
            )

            return {
                "text": f"# LLM 流式调用失败\n{error_msg}",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "model": self.model_id
            }

    def __repr__(self) -> str:
        return f"BedrockLLM(model={self.model_id}, region={self.region})"


# 便捷工厂函数
def create_sonnet_llm(**kwargs) -> BedrockLLM:
    """创建 Claude Sonnet 4.5 LLM"""
    return BedrockLLM(model="sonnet", **kwargs)


def create_haiku_llm(**kwargs) -> BedrockLLM:
    """创建 Claude 3.5 Haiku LLM"""
    return BedrockLLM(model="haiku", **kwargs)
