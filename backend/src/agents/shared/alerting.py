"""
Alerting System - Option A Day 3

生产级告警系统，提供：
- Email/Slack/Webhook 多渠道告警
- 告警规则配置（错误率、超时、内存）
- 告警降噪（静默期、聚合、频率限制）
- 告警历史记录
"""

import time
import json
import smtplib
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
import urllib.request
import urllib.parse

from .structured_logger import get_logger
from .metrics_collector import get_metrics_collector
from .error_tracker import ErrorRecord, ErrorSeverity, get_error_tracker


class AlertChannel(Enum):
    """告警渠道"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG_ONLY = "log_only"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """告警规则"""
    name: str                          # 规则名称
    description: str                   # 规则描述
    condition: Callable[[], bool]      # 触发条件（返回True则触发）
    level: AlertLevel                  # 告警级别
    channels: List[AlertChannel]       # 告警渠道

    # 降噪配置
    cooldown_seconds: int = 300        # 静默期（秒）- 触发后N秒内不再触发
    max_alerts_per_hour: int = 10      # 每小时最大告警数

    # 聚合配置
    aggregate_window_seconds: int = 60  # 聚合窗口（秒）
    aggregate_count_threshold: int = 1  # 聚合阈值（窗口内触发N次才发送）

    enabled: bool = True               # 是否启用

    # 内部状态
    last_alert_time: float = 0         # 上次告警时间
    alert_count_this_hour: int = 0     # 本小时告警次数
    hour_reset_time: float = 0         # 小时重置时间
    pending_alerts: List[float] = field(default_factory=list)  # 待聚合的告警时间戳


@dataclass
class Alert:
    """告警消息"""
    alert_id: str                      # 告警ID
    rule_name: str                     # 规则名称
    level: AlertLevel                  # 告警级别
    title: str                         # 告警标题
    message: str                       # 告警消息
    timestamp: float                   # 时间戳
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    channels: List[AlertChannel] = field(default_factory=list)  # 发送渠道


class EmailChannel:
    """Email 告警渠道"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: List[str],
        use_tls: bool = True
    ):
        """
        初始化 Email 渠道

        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码
            from_email: 发件人邮箱
            to_emails: 收件人邮箱列表
            use_tls: 是否使用TLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

        self.logger = get_logger("EmailChannel")

    def send(self, alert: Alert) -> bool:
        """
        发送告警邮件

        Args:
            alert: 告警消息

        Returns:
            bool: 是否发送成功
        """
        try:
            # 构造邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)

            # HTML 内容
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .alert-box {{
                        padding: 20px;
                        border-left: 5px solid {self._get_color_for_level(alert.level)};
                        background-color: #f9f9f9;
                    }}
                    .alert-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                    .alert-message {{ margin: 10px 0; }}
                    .alert-context {{ margin-top: 15px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="alert-box">
                    <div class="alert-title">{alert.title}</div>
                    <div class="alert-message">{alert.message}</div>
                    <div class="alert-context">
                        <strong>Rule:</strong> {alert.rule_name}<br>
                        <strong>Time:</strong> {datetime.fromtimestamp(alert.timestamp).isoformat()}<br>
                        <strong>Alert ID:</strong> {alert.alert_id}
                    </div>
                    {self._format_context(alert.context)}
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_body, 'html'))

            # 发送邮件
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, self.to_emails, msg.as_string())
            server.quit()

            self.logger.info("Email告警发送成功",
                           alert_id=alert.alert_id,
                           to_emails=self.to_emails)
            return True

        except Exception as e:
            self.logger.error("Email告警发送失败",
                            alert_id=alert.alert_id,
                            error=str(e))
            return False

    @staticmethod
    def _get_color_for_level(level: AlertLevel) -> str:
        """获取告警级别对应的颜色"""
        colors = {
            AlertLevel.INFO: "#3498db",      # 蓝色
            AlertLevel.WARNING: "#f39c12",   # 橙色
            AlertLevel.ERROR: "#e74c3c",     # 红色
            AlertLevel.CRITICAL: "#c0392b"   # 深红色
        }
        return colors.get(level, "#95a5a6")

    @staticmethod
    def _format_context(context: Dict[str, Any]) -> str:
        """格式化上下文信息"""
        if not context:
            return ""

        items = []
        for key, value in context.items():
            items.append(f"<strong>{key}:</strong> {value}")

        return f'<div class="alert-context">{"<br>".join(items)}</div>'


class SlackChannel:
    """Slack 告警渠道"""

    def __init__(self, webhook_url: str):
        """
        初始化 Slack 渠道

        Args:
            webhook_url: Slack Webhook URL
        """
        self.webhook_url = webhook_url
        self.logger = get_logger("SlackChannel")

    def send(self, alert: Alert) -> bool:
        """
        发送 Slack 告警

        Args:
            alert: 告警消息

        Returns:
            bool: 是否发送成功
        """
        try:
            # 构造 Slack 消息
            payload = {
                "text": f"*{alert.title}*",
                "attachments": [
                    {
                        "color": self._get_color_for_level(alert.level),
                        "fields": [
                            {
                                "title": "Level",
                                "value": alert.level.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Rule",
                                "value": alert.rule_name,
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": alert.message,
                                "short": False
                            },
                            {
                                "title": "Time",
                                "value": datetime.fromtimestamp(alert.timestamp).isoformat(),
                                "short": True
                            },
                            {
                                "title": "Alert ID",
                                "value": alert.alert_id,
                                "short": True
                            }
                        ]
                    }
                ]
            }

            # 添加上下文字段
            if alert.context:
                for key, value in alert.context.items():
                    payload["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })

            # 发送 HTTP POST
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            response = urllib.request.urlopen(req, timeout=10)

            if response.status == 200:
                self.logger.info("Slack告警发送成功", alert_id=alert.alert_id)
                return True
            else:
                self.logger.error("Slack告警发送失败",
                                alert_id=alert.alert_id,
                                status_code=response.status)
                return False

        except Exception as e:
            self.logger.error("Slack告警发送失败",
                            alert_id=alert.alert_id,
                            error=str(e))
            return False

    @staticmethod
    def _get_color_for_level(level: AlertLevel) -> str:
        """获取告警级别对应的颜色"""
        colors = {
            AlertLevel.INFO: "#3498db",
            AlertLevel.WARNING: "#f39c12",
            AlertLevel.ERROR: "#e74c3c",
            AlertLevel.CRITICAL: "#c0392b"
        }
        return colors.get(level, "#95a5a6")


class WebhookChannel:
    """通用 Webhook 告警渠道"""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        """
        初始化 Webhook 渠道

        Args:
            webhook_url: Webhook URL
            headers: 自定义请求头
        """
        self.webhook_url = webhook_url
        self.headers = headers or {}
        self.logger = get_logger("WebhookChannel")

    def send(self, alert: Alert) -> bool:
        """
        发送 Webhook 告警

        Args:
            alert: 告警消息

        Returns:
            bool: 是否发送成功
        """
        try:
            # 构造 JSON payload
            payload = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "timestamp_iso": datetime.fromtimestamp(alert.timestamp).isoformat(),
                "context": alert.context
            }

            # 发送 HTTP POST
            data = json.dumps(payload).encode('utf-8')
            headers = {'Content-Type': 'application/json', **self.headers}

            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers=headers
            )

            response = urllib.request.urlopen(req, timeout=10)

            if response.status == 200:
                self.logger.info("Webhook告警发送成功", alert_id=alert.alert_id)
                return True
            else:
                self.logger.error("Webhook告警发送失败",
                                alert_id=alert.alert_id,
                                status_code=response.status)
                return False

        except Exception as e:
            self.logger.error("Webhook告警发送失败",
                            alert_id=alert.alert_id,
                            error=str(e))
            return False


class AlertManager:
    """
    告警管理器

    管理告警规则、发送告警、降噪处理
    """

    def __init__(self):
        """初始化告警管理器"""
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[AlertChannel, Any] = {}

        # 告警历史（最近1000条）
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000

        # 线程锁
        self.lock = threading.Lock()

        # 集成
        self.logger = get_logger("AlertManager", level="INFO")
        self.metrics = get_metrics_collector()
        self.error_tracker = get_error_tracker()

        self.logger.info("AlertManager初始化")

    def register_channel(self, channel_type: AlertChannel, channel: Any):
        """
        注册告警渠道

        Args:
            channel_type: 渠道类型
            channel: 渠道实例（EmailChannel, SlackChannel, WebhookChannel）
        """
        self.channels[channel_type] = channel
        self.logger.info("告警渠道注册", channel=channel_type.value)

    def add_rule(self, rule: AlertRule):
        """
        添加告警规则

        Args:
            rule: 告警规则
        """
        with self.lock:
            self.rules[rule.name] = rule
            self.logger.info("告警规则添加",
                           rule_name=rule.name,
                           level=rule.level.value,
                           channels=[c.value for c in rule.channels])

    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        with self.lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                self.logger.info("告警规则移除", rule_name=rule_name)

    def enable_rule(self, rule_name: str):
        """启用规则"""
        with self.lock:
            if rule_name in self.rules:
                self.rules[rule_name].enabled = True
                self.logger.info("告警规则启用", rule_name=rule_name)

    def disable_rule(self, rule_name: str):
        """禁用规则"""
        with self.lock:
            if rule_name in self.rules:
                self.rules[rule_name].enabled = False
                self.logger.info("告警规则禁用", rule_name=rule_name)

    def check_rules(self):
        """
        检查所有规则（应定期调用）

        遍历所有规则，检查触发条件，并应用降噪逻辑
        """
        current_time = time.time()

        with self.lock:
            for rule_name, rule in self.rules.items():
                if not rule.enabled:
                    continue

                try:
                    # 检查触发条件
                    if rule.condition():
                        # 应用降噪逻辑
                        if self._should_send_alert(rule, current_time):
                            # 生成并发送告警
                            alert = self._create_alert(rule, current_time)
                            self._send_alert(alert)
                            self._update_rule_state(rule, current_time)

                except Exception as e:
                    self.logger.error("告警规则检查失败",
                                    rule_name=rule_name,
                                    error=str(e))

    def _should_send_alert(self, rule: AlertRule, current_time: float) -> bool:
        """
        判断是否应该发送告警（降噪逻辑）

        Args:
            rule: 告警规则
            current_time: 当前时间

        Returns:
            bool: 是否发送
        """
        # 1. 检查静默期（cooldown）
        if current_time - rule.last_alert_time < rule.cooldown_seconds:
            return False

        # 2. 检查每小时最大告警数
        # 重置计数器（如果已经过去一小时）
        if current_time - rule.hour_reset_time >= 3600:
            rule.alert_count_this_hour = 0
            rule.hour_reset_time = current_time

        if rule.alert_count_this_hour >= rule.max_alerts_per_hour:
            return False

        # 3. 聚合逻辑
        if rule.aggregate_count_threshold > 1:
            # 添加到待聚合列表
            rule.pending_alerts.append(current_time)

            # 清理过期的待聚合告警
            window_start = current_time - rule.aggregate_window_seconds
            rule.pending_alerts = [
                t for t in rule.pending_alerts if t >= window_start
            ]

            # 检查是否达到聚合阈值
            if len(rule.pending_alerts) < rule.aggregate_count_threshold:
                return False

            # 达到阈值，清空待聚合列表
            rule.pending_alerts.clear()

        return True

    def _create_alert(self, rule: AlertRule, timestamp: float) -> Alert:
        """创建告警消息"""
        import hashlib

        # 生成告警ID
        alert_id = hashlib.sha256(
            f"{rule.name}:{timestamp}".encode()
        ).hexdigest()[:16]

        # 构造告警消息
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            level=rule.level,
            title=f"Alert: {rule.name}",
            message=rule.description,
            timestamp=timestamp,
            channels=rule.channels,
            context={}
        )

        return alert

    def _send_alert(self, alert: Alert):
        """发送告警到各个渠道"""
        for channel_type in alert.channels:
            if channel_type == AlertChannel.LOG_ONLY:
                # 仅记录日志
                self.logger.warning(
                    "告警触发（仅日志）",
                    alert_id=alert.alert_id,
                    rule_name=alert.rule_name,
                    level=alert.level.value,
                    message=alert.message
                )
                continue

            # 获取渠道实例
            channel = self.channels.get(channel_type)
            if channel is None:
                self.logger.warning(
                    "告警渠道未注册",
                    channel=channel_type.value,
                    alert_id=alert.alert_id
                )
                continue

            # 发送
            try:
                success = channel.send(alert)
                if success:
                    self.metrics.increment(
                        "alerts_sent_total",
                        labels={
                            "channel": channel_type.value,
                            "level": alert.level.value,
                            "status": "success"
                        }
                    )
                else:
                    self.metrics.increment(
                        "alerts_sent_total",
                        labels={
                            "channel": channel_type.value,
                            "level": alert.level.value,
                            "status": "failure"
                        }
                    )
            except Exception as e:
                self.logger.error(
                    "告警发送异常",
                    channel=channel_type.value,
                    alert_id=alert.alert_id,
                    error=str(e)
                )

        # 记录到历史
        with self.lock:
            self.alert_history.append(alert)
            if len(self.alert_history) > self.max_history_size:
                self.alert_history.pop(0)

    def _update_rule_state(self, rule: AlertRule, current_time: float):
        """更新规则状态"""
        rule.last_alert_time = current_time
        rule.alert_count_this_hour += 1

    def get_alert_history(self, limit: int = 10) -> List[Alert]:
        """获取告警历史"""
        with self.lock:
            return self.alert_history[-limit:]

    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警统计摘要"""
        with self.lock:
            total_rules = len(self.rules)
            enabled_rules = sum(1 for r in self.rules.values() if r.enabled)
            total_alerts = len(self.alert_history)

            by_level = {}
            for alert in self.alert_history:
                level = alert.level.value
                by_level[level] = by_level.get(level, 0) + 1

            return {
                "total_rules": total_rules,
                "enabled_rules": enabled_rules,
                "disabled_rules": total_rules - enabled_rules,
                "total_alerts_sent": total_alerts,
                "alerts_by_level": by_level,
                "registered_channels": [c.value for c in self.channels.keys()]
            }


# 全局单例
_global_alert_manager: Optional[AlertManager] = None
_manager_lock = threading.Lock()


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器（单例）"""
    global _global_alert_manager

    if _global_alert_manager is None:
        with _manager_lock:
            if _global_alert_manager is None:
                _global_alert_manager = AlertManager()

    return _global_alert_manager
