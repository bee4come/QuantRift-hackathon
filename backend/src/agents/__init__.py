"""
Rift Rewind Agents - Production Agent System
基于 Google ADK + AWS Bedrock AgentCore 的生产级 Agent 系统
"""

__version__ = "1.0.0"
__author__ = "Rift Rewind Team"

from .shared import (
    BedrockLLM,
    BedrockModel,
    AgentConfig,
    get_config,
    PromptTemplate
)

__all__ = [
    'BedrockLLM',
    'BedrockModel',
    'AgentConfig',
    'get_config',
    'PromptTemplate'
]
