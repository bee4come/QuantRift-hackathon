"""
Agent 配置管理
环境变量加载和全局配置
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """Agent 全局配置"""

    # AWS 配置
    aws_region: str = "us-west-2"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Bedrock 模型配置
    default_model: str = "sonnet"  # sonnet 或 haiku
    read_timeout: int = 600
    connect_timeout: int = 60
    max_retries: int = 3

    # LLM 生成参数
    max_tokens: int = 16000
    temperature: float = 0.7

    # Agent 特定配置
    agent_name: str = "RiftRewindAgent"
    app_name: str = "rift-rewind-agents"

    # 路径配置
    project_root: Path = field(default_factory=lambda: Path("/home/zty/rift_rewind"))

    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """
        从环境变量加载配置

        优先从 .env 文件加载，然后从系统环境变量覆盖
        """
        # 加载 .env 文件
        env_file = Path("/home/zty/rift_rewind/.env")
        if env_file.exists():
            load_env_file(env_file)

        return cls(
            aws_region=os.getenv("AWS_REGION", "us-west-2"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            default_model=os.getenv("AGENT_DEFAULT_MODEL", "sonnet"),
            max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "16000")),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.7")),
            agent_name=os.getenv("AGENT_NAME", "RiftRewindAgent"),
            app_name=os.getenv("AGENT_APP_NAME", "rift-rewind-agents")
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "aws_region": self.aws_region,
            "default_model": self.default_model,
            "read_timeout": self.read_timeout,
            "connect_timeout": self.connect_timeout,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "agent_name": self.agent_name,
            "app_name": self.app_name
        }


def load_env_file(env_file: Path) -> None:
    """
    加载 .env 文件到环境变量

    Args:
        env_file: .env 文件路径
    """
    if not env_file.exists():
        return

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value


# 全局配置实例
_config: Optional[AgentConfig] = None


def get_config() -> AgentConfig:
    """
    获取全局配置实例（单例模式）

    Returns:
        AgentConfig: 全局配置
    """
    global _config
    if _config is None:
        _config = AgentConfig.from_env()
    return _config


def reload_config() -> AgentConfig:
    """
    重新加载配置

    Returns:
        AgentConfig: 新的配置实例
    """
    global _config
    _config = AgentConfig.from_env()
    return _config
