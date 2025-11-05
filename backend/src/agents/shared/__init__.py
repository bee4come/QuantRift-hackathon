"""
Rift Rewind Agents - Shared Modules
共享模块：Bedrock 适配器、配置管理、Prompt 模板
"""

from .bedrock_adapter import BedrockLLM, BedrockModel
from .config import AgentConfig, get_config
from .prompts import PromptTemplate

__all__ = [
    'BedrockLLM',
    'BedrockModel',
    'AgentConfig',
    'get_config',
    'PromptTemplate'
]
