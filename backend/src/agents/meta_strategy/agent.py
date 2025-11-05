"""
MetaStrategyAgent - Meta-Strategy Orchestration Agent

全局调度中枢，负责解析用户请求、协调多个专项Agent、综合分析结果。
"""

import json
import time
import yaml
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .context import AgentContext
from .tools import (
    get_agent_registry,
    parse_request_classification,
    determine_agent_workflow,
    execute_agent_workflow,
    format_strategy_summary
)
from .prompts import (
    build_request_classification_prompt,
    build_synthesis_prompt
)


class MetaStrategyAgent:
    """
    元策略Agent - 全局调度中枢

    作为整个Agent生态的"大脑"，负责：
    1. 解析用户复杂请求
    2. 制定最优分析策略
    3. 协调多个专项Agent执行
    4. 综合多源分析结果
    5. 生成统一输出报告
    """

    def __init__(self, model: str = "haiku", workflows_path: Optional[str] = None):
        """
        初始化元策略Agent

        Args:
            model: LLM模型选择 ("sonnet" for 强分析, "haiku" for 快速调度)
            workflows_path: workflows.yml 配置文件路径（默认使用同目录下的）
        """
        self.config = get_config()
        self.llm = BedrockLLM(model=model)
        self.agent_registry = get_agent_registry()

        # 加载工作流配置
        if workflows_path is None:
            workflows_path = Path(__file__).parent / "workflows.yml"

        self.workflows = self._load_workflows(workflows_path)
        self.agent_classes = self.workflows.get("agent_classes", {})

    def run(
        self,
        user_request: str,
        packs_dir: str,
        output_dir: Optional[str] = None,
        agent_model: str = "sonnet"
    ) -> Tuple[Dict[str, Any], str]:
        """
        运行元策略分析

        Args:
            user_request: 用户自然语言请求
            packs_dir: Player Pack数据目录
            output_dir: 输出目录（可选）
            agent_model: 子Agent使用的模型 ("sonnet" or "haiku")

        Returns:
            (strategy_data, synthesis_report) - 策略数据和综合报告
        """
        start_time = time.time()

        print(f"\n{'='*70}")
        print(f"🧠 元策略Agent - 全局调度中枢")
        print(f"{'='*70}\n")
        print(f"📝 用户请求: {user_request}\n")

        # 步骤1: 请求分类
        print("🔍 步骤1: 分析用户意图...")
        classification = self._classify_request(user_request)

        request_type = classification.get("request_type", "comprehensive_analysis")
        confidence = classification.get("confidence", 0.0)
        focus_areas = classification.get("focus_areas", [])

        print(f"   ✅ 分类结果: {request_type} (置信度: {confidence:.1%})")
        print(f"   关注领域: {', '.join(focus_areas)}\n")

        # 步骤2: 确定工作流
        print("🎯 步骤2: 制定分析策略...")
        workflow = determine_agent_workflow(
            request_type=request_type,
            focus_areas=focus_areas,
            packs_dir=packs_dir
        )

        agents_to_invoke = [a["name"] for a in workflow.get("agents", [])]
        execution_mode = workflow.get("execution_mode", "sequential")

        print(f"   执行模式: {execution_mode}")
        print(f"   调用Agent: {', '.join(agents_to_invoke)}\n")

        if not agents_to_invoke:
            print("⚠️  警告: 未找到合适的Agent执行该请求")
            return self._create_empty_result(user_request, request_type)

        # 创建Agent执行上下文
        context = AgentContext(
            user_request=user_request,
            packs_dir=packs_dir
        )

        # 步骤3: 执行Agent工作流（带上下文传递）
        print(f"🚀 步骤3: 执行Agent工作流 ({len(agents_to_invoke)}个Agent)...")
        print("="*70)

        agent_results = execute_agent_workflow(
            workflow=workflow,
            agent_registry=self.agent_registry,
            context=context,
            model=agent_model
        )

        print("="*70)
        print(f"✅ Agent执行完成\n")

        # 打印上下文摘要
        ctx_summary = context.get_summary()
        print(f"📊 上下文摘要:")
        print(f"   执行了 {ctx_summary['total_agents_executed']} 个Agent")
        print(f"   执行顺序: {' → '.join(ctx_summary['execution_order'])}\n")

        # 步骤4: 综合分析结果
        print("🧩 步骤4: 综合分析结果...")

        strategy_info = {
            "request_type": request_type,
            "agents_invoked": agents_to_invoke,
            "execution_mode": execution_mode,
            "classification": classification
        }

        synthesis_report = self._synthesize_results(
            user_request=user_request,
            strategy=strategy_info,
            agent_results=agent_results
        )

        execution_time = time.time() - start_time

        print(f"   ✅ 综合报告生成完成 ({len(synthesis_report)} 字符)")
        print(f"   ⏱️  总执行时间: {execution_time:.1f}秒\n")

        # 步骤5: 组装完整输出（包含上下文）
        output_data = {
            "strategy": strategy_info,
            "agent_results": agent_results,
            "synthesis": synthesis_report,
            "context_summary": context.get_summary(),
            "metadata": {
                "user_request": user_request,
                "execution_time": round(execution_time, 2),
                "model_used": {
                    "orchestrator": self.llm.model_id,
                    "agents": agent_model
                }
            }
        }

        # 步骤6: 保存输出（包括上下文）
        if output_dir:
            self._save_outputs(output_dir, output_data, synthesis_report, context)

        return output_data, synthesis_report

    def _classify_request(self, user_request: str) -> Dict[str, Any]:
        """分类用户请求"""
        prompts = build_request_classification_prompt(user_request)

        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=1000
        )

        classification = parse_request_classification(result["text"])
        return classification

    def _synthesize_results(
        self,
        user_request: str,
        strategy: Dict[str, Any],
        agent_results: Dict[str, Any]
    ) -> str:
        """综合多个Agent的分析结果"""
        prompts = build_synthesis_prompt(
            user_request=user_request,
            strategy=strategy,
            agent_results=agent_results
        )

        # 使用Sonnet进行高质量综合
        synthesis_llm = BedrockLLM(model="sonnet")

        result = synthesis_llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=16000
        )

        return result["text"]

    def _create_empty_result(
        self,
        user_request: str,
        request_type: str
    ) -> Tuple[Dict[str, Any], str]:
        """创建空结果（当没有合适的Agent时）"""
        output_data = {
            "strategy": {
                "request_type": request_type,
                "agents_invoked": [],
                "execution_mode": "none"
            },
            "agent_results": {},
            "synthesis": "抱歉，暂时无法处理该类型的请求。",
            "metadata": {
                "user_request": user_request,
                "error": "No suitable agent found"
            }
        }

        report = f"""# 分析请求未能处理

**用户请求**: {user_request}

**原因**: 暂未实现支持该类型请求的Agent。

**建议**: 请尝试以下类型的请求：
- 综合分析: "给我一个全面的赛季分析"
- 快速诊断: "我最近的问题在哪？"
- 英雄推荐: "推荐几个适合我的英雄"
"""

        return output_data, report

    def _save_outputs(
        self,
        output_dir: str,
        output_data: Dict[str, Any],
        synthesis_report: str,
        context: AgentContext
    ) -> None:
        """保存输出文件（包括上下文）"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存策略数据
        strategy_file = output_path / "meta_strategy_result.json"
        with open(strategy_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # 保存综合报告
        report_file = output_path / "meta_strategy_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(synthesis_report)

        # 保存上下文
        context_file = output_path / "agent_context.json"
        context.save(str(context_file))

        print(f"💾 输出已保存:")
        print(f"   - {strategy_file}")
        print(f"   - {report_file}")
        print(f"   - {context_file}")

    def _load_workflows(self, workflows_path: Path) -> Dict[str, Any]:
        """加载工作流配置"""
        if not workflows_path.exists():
            print(f"⚠️  警告: 工作流配置文件不存在: {workflows_path}")
            return {}

        with open(workflows_path, 'r', encoding='utf-8') as f:
            workflows = yaml.safe_load(f)

        workflow_count = len([k for k in workflows.keys() if k not in ['agent_classes', 'default_params']])
        print(f"✅ 加载工作流配置: {workflow_count} 个工作流")
        return workflows

    def run_workflow(
        self,
        workflow_name: str,
        params: Dict[str, Any],
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        运行预定义工作流

        Args:
            workflow_name: 工作流名称 (quick_diagnosis, comprehensive_profile, etc.)
            params: 工作流参数 (packs_dir, rank, main_role, etc.)
            output_dir: 输出目录

        Returns:
            完整执行结果，包含所有Agent输出和性能指标
        """
        start_time = time.time()

        print(f"\n{'='*70}")
        print(f"🎯 运行预定义工作流: {workflow_name}")
        print(f"{'='*70}\n")

        # 验证工作流存在
        if workflow_name not in self.workflows:
            available = [k for k in self.workflows.keys() if k not in ['agent_classes', 'default_params']]
            raise ValueError(f"工作流 '{workflow_name}' 不存在。可用工作流: {available}")

        workflow_config = self.workflows[workflow_name]
        print(f"📝 工作流描述: {workflow_config.get('description', 'N/A')}")
        print(f"⏱️  预估时间: {workflow_config.get('estimated_time', 'N/A')}")
        print(f"⚡ 效率提升: {workflow_config.get('efficiency_gain', 'N/A')}\n")

        # 创建 AgentContext
        context = AgentContext(
            user_request=f"执行工作流: {workflow_name}",
            packs_dir=params.get("packs_dir", "")
        )

        # 执行各阶段
        phases = workflow_config.get("phases", [])
        all_results = {}

        for phase_config in phases:
            phase_num = phase_config["phase"]
            phase_name = phase_config.get("name", f"Phase {phase_num}")
            agents = phase_config["agents"]
            mode = phase_config.get("mode", "sequential")

            print(f"{'='*70}")
            print(f"📍 Phase {phase_num}: {phase_name}")
            print(f"   模式: {mode}, Agent数: {len(agents)}")
            print(f"{'='*70}\n")

            # 执行该阶段的所有 Agent
            phase_results = self._execute_phase(
                phase_config=phase_config,
                params=params,
                context=context,
                output_dir=output_dir
            )

            all_results.update(phase_results)

        execution_time = time.time() - start_time

        # 汇总结果
        result = {
            "workflow_name": workflow_name,
            "workflow_config": workflow_config,
            "execution_time": round(execution_time, 2),
            "agent_results": all_results,
            "context_summary": context.get_summary(),
            "performance_metrics": {
                "total_agents": len(all_results),
                "execution_time_seconds": round(execution_time, 2),
                "estimated_time": workflow_config.get("estimated_time", "N/A"),
                "efficiency_gain": workflow_config.get("efficiency_gain", "N/A")
            }
        }

        print(f"\n{'='*70}")
        print(f"✅ 工作流执行完成")
        print(f"⏱️  实际执行时间: {execution_time:.1f}秒")
        print(f"📊 完成 Agent 数: {len(all_results)}")
        print(f"{'='*70}\n")

        # 保存结果
        if output_dir:
            self._save_workflow_results(result, output_dir, context)

        return result

    def _execute_phase(
        self,
        phase_config: Dict[str, Any],
        params: Dict[str, Any],
        context: AgentContext,
        output_dir: Optional[str]
    ) -> Dict[str, Any]:
        """执行工作流的一个阶段"""
        agents = phase_config["agents"]
        mode = phase_config.get("mode", "sequential")
        phase_results = {}

        # 检查是否需要动态生成 agents (Role Mastery Phase 3)
        dynamic_count = phase_config.get("dynamic_count")
        params_source = phase_config.get("params_source")

        if dynamic_count and params_source:
            # 动态生成 agents
            print(f"🧩 动态生成 {dynamic_count} 个 Agent (基于 {params_source})...")
            agents = self._generate_dynamic_agents(
                agent_template=agents[0] if agents else {},
                dynamic_count=dynamic_count,
                params_source=params_source,
                context=context,
                params=params
            )
            print(f"   ✅ 生成了 {len(agents)} 个 Agent 配置\n")

        # 如果没有可执行的 Agent，直接返回
        if not agents:
            print("⚠️  警告: 该阶段没有可执行的Agent，跳过")
            return phase_results

        if mode == "sequential":
            # 串行执行
            for agent_config in agents:
                agent_name = agent_config["name"]
                result = self._execute_single_agent(
                    agent_config=agent_config,
                    params=params,
                    context=context,
                    output_dir=output_dir
                )
                phase_results[agent_name] = result

        elif mode == "parallel":
            # 并行执行
            with ThreadPoolExecutor(max_workers=len(agents)) as executor:
                futures = {}
                for agent_config in agents:
                    agent_name = agent_config["name"]
                    future = executor.submit(
                        self._execute_single_agent,
                        agent_config=agent_config,
                        params=params,
                        context=context,
                        output_dir=output_dir
                    )
                    futures[future] = agent_name

                for future in as_completed(futures):
                    agent_name = futures[future]
                    try:
                        result = future.result()
                        phase_results[agent_name] = result
                    except Exception as e:
                        print(f"❌ Agent {agent_name} 执行失败: {e}")
                        phase_results[agent_name] = {"error": str(e)}

        return phase_results

    def _generate_dynamic_agents(
        self,
        agent_template: Dict[str, Any],
        dynamic_count: int,
        params_source: str,
        context: AgentContext,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        动态生成多个 Agent 配置

        用于 Role Mastery Phase 3: 基于 Phase 2 结果动态生成 N 个 ChampionMasteryAgent

        Args:
            agent_template: Agent 配置模板
            dynamic_count: 生成 Agent 数量
            params_source: 参数来源标识 (例如 "phase2_top_champions")
            context: Agent 执行上下文
            params: 用户参数

        Returns:
            生成的 Agent 配置列表
        """
        # 提取 champion IDs (根据 params_source 类型)
        champion_ids = []

        if params_source == "phase2_top_champions":
            # 从 role_specialization 结果中提取 top champions
            role_spec_result = context.get_agent_result("role_specialization")

            # 从 AgentContext 获取 role_specialization 的 data
            if role_spec_result and "data" in role_spec_result:
                data = role_spec_result["data"]

                # 从 champion_pool.depth.core 中提取 top champions
                if isinstance(data, dict):
                    # RoleSpecializationAgent 的实际数据结构
                    if "champion_pool" in data and "depth" in data["champion_pool"]:
                        depth = data["champion_pool"]["depth"]
                        if "core" in depth and isinstance(depth["core"], list):
                            # core 是按 games 排序的 champion 列表
                            core_champions = depth["core"][:dynamic_count]
                            champion_ids = [c["champion_id"] for c in core_champions if "champion_id" in c]

                    # 兼容旧格式 (以防其他地方使用不同格式)
                    elif "top_champions" in data:
                        champion_ids = data["top_champions"][:dynamic_count]
                    elif "core_champions" in data:
                        champion_ids = data["core_champions"][:dynamic_count]
                    elif "champion_stats" in data:
                        # 从 champion_stats 中提取前 N 个
                        champ_stats = data["champion_stats"]
                        if isinstance(champ_stats, list):
                            champion_ids = [c.get("champion_id") for c in champ_stats[:dynamic_count] if "champion_id" in c]
                        elif isinstance(champ_stats, dict):
                            # Dict 格式，按 games 或 winrate 排序
                            sorted_champs = sorted(
                                champ_stats.items(),
                                key=lambda x: x[1].get("games", 0),
                                reverse=True
                            )
                            champion_ids = [int(champ_id) for champ_id, _ in sorted_champs[:dynamic_count]]

        # 如果无法提取，返回空列表
        if not champion_ids:
            print(f"   ⚠️  警告: 无法从 {params_source} 提取 champion IDs")
            return []

        print(f"   📊 提取到 {len(champion_ids)} 个英雄 ID: {champion_ids}")

        # 生成 Agent 配置
        generated_agents = []
        for i, champion_id in enumerate(champion_ids):
            # 复制模板
            agent_config = agent_template.copy()

            # 修改 name 和 champion_id 参数
            agent_config["name"] = f"champion_mastery_{champion_id}"

            # 更新 params 中的 champion_id
            agent_params = agent_config.get("params", {}).copy()
            agent_params["champion_id"] = champion_id
            agent_config["params"] = agent_params

            generated_agents.append(agent_config)

        return generated_agents

    def _execute_single_agent(
        self,
        agent_config: Dict[str, Any],
        params: Dict[str, Any],
        context: AgentContext,
        output_dir: Optional[str]
    ) -> Dict[str, Any]:
        """执行单个 Agent"""
        agent_start_time = time.time()

        agent_name = agent_config["name"]
        agent_class_name = agent_config.get("class")
        agent_params = agent_config.get("params", {})
        agent_init_params = agent_config.get("init_params", {})
        use_cache = agent_config.get("use_cache")

        print(f"🚀 执行 {agent_name}...")

        # 替换参数模板
        resolved_params = self._resolve_params(agent_params, params, context)
        resolved_init_params = self._resolve_params(agent_init_params, params, context)

        # 加载 Agent 类 (优先使用 agent_name 在 agent_classes 中查找)
        agent_class = self._load_agent_class(agent_name, agent_class_name)
        if agent_class is None:
            return {"error": f"无法加载 Agent 类: {agent_class_name}"}

        # 创建 Agent 实例 (传入初始化参数)
        agent = agent_class(**resolved_init_params)

        # 如果需要使用缓存，从 context 获取
        if use_cache:
            cached_data = context.get_shared_data(use_cache)
            if cached_data:
                print(f"   ✅ 使用缓存数据: {use_cache}")

        # 执行 Agent (传入 context)
        try:
            # 检查 Agent 的 run 方法是否接受 context 参数
            import inspect
            run_signature = inspect.signature(agent.run)
            if "context" in run_signature.parameters:
                result = agent.run(**resolved_params, context=context)
            else:
                result = agent.run(**resolved_params)

            # 记录结果到 context (Agent返回 (data, report) 元组)
            if isinstance(result, tuple) and len(result) == 2:
                data, report = result
                context.add_agent_result(agent_name, data, report)
            else:
                # 非标准格式，直接记录
                data = {}
                report = str(result)
                context.add_agent_result(agent_name, data, report)

            # 如果配置了缓存输出，将结果存入 context
            cache_output = agent_config.get("cache_output")
            if cache_output and isinstance(result, tuple):
                analysis_data = result[0] if len(result) > 0 else {}
                if "all_packs" in analysis_data:  # AnnualSummaryAgent
                    context.add_shared_data(
                        cache_output,
                        analysis_data["all_packs"],
                        summary=f"全部数据缓存 from {agent_name}"
                    )

            agent_execution_time = time.time() - agent_start_time
            print(f"   ✅ {agent_name} 完成 ({agent_execution_time:.1f}秒)\n")

            # Return flattened structure for tests
            if isinstance(result, tuple) and len(result) == 2:
                data, report = result
                return {
                    "status": "success",
                    "data": data,
                    "report": report,
                    "execution_time": round(agent_execution_time, 2)
                }
            else:
                return {
                    "status": "success",
                    "data": {},
                    "report": str(result),
                    "execution_time": round(agent_execution_time, 2)
                }

        except Exception as e:
            agent_execution_time = time.time() - agent_start_time
            print(f"   ❌ {agent_name} 失败: {e}\n")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": round(agent_execution_time, 2)
            }

    def _resolve_params(
        self,
        template_params: Dict[str, Any],
        user_params: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """解析参数模板，将 {param_name} 替换为实际值"""
        resolved = {}
        for key, value in template_params.items():
            if isinstance(value, str) and "{" in value and "}" in value:
                # 包含模板参数，进行替换
                resolved_value = value
                # 找到所有 {param_name} 并替换
                import re
                for match in re.finditer(r'\{(\w+)\}', value):
                    param_name = match.group(1)
                    param_value = user_params.get(param_name, match.group(0))
                    resolved_value = resolved_value.replace(match.group(0), str(param_value))
                resolved[key] = resolved_value
            else:
                resolved[key] = value
        return resolved

    def _load_agent_class(self, agent_name: str, class_name: Optional[str] = None):
        """
        动态加载 Agent 类

        Args:
            agent_name: Agent名称 (用于在agent_classes中查找)
            class_name: 类名 (备用，如果agent_name查找失败)
        """
        # 优先使用 agent_name 在 agent_classes 映射中查找
        full_path = None

        if agent_name in self.agent_classes:
            full_path = self.agent_classes[agent_name]
        else:
            # 处理动态生成的 agent (如 champion_mastery_92)
            # 尝试提取基础名称 (去掉数字后缀)
            import re
            base_name_match = re.match(r'^([a-z_]+)_\d+$', agent_name)
            if base_name_match:
                base_name = base_name_match.group(1)
                if base_name in self.agent_classes:
                    full_path = self.agent_classes[base_name]

        if not full_path and class_name and class_name in self.agent_classes:
            full_path = self.agent_classes[class_name]
        elif not full_path and class_name:
            full_path = class_name

        if not full_path:
            print(f"❌ Agent {agent_name} 未在 agent_classes 中找到映射")
            return None

        try:
            # 检查是否包含模块路径
            if "." not in full_path:
                print(f"❌ Agent 类 {full_path} 缺少模块路径")
                return None

            module_path, cls_name = full_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            agent_class = getattr(module, cls_name)
            return agent_class
        except Exception as e:
            print(f"❌ 无法加载 Agent 类 {full_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _save_workflow_results(
        self,
        result: Dict[str, Any],
        output_dir: str,
        context: AgentContext
    ) -> None:
        """保存工作流执行结果"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存完整结果
        result_file = output_path / "workflow_result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        # 保存 context
        context_file = output_path / "workflow_context.json"
        context.save(str(context_file))

        print(f"💾 工作流结果已保存:")
        print(f"   - {result_file}")
        print(f"   - {context_file}")


def create_meta_strategy_agent(model: str = "haiku") -> MetaStrategyAgent:
    """
    工厂函数：创建元策略Agent

    Args:
        model: LLM模型选择 ("haiku" for 快速调度, "sonnet" for 强分析)

    Returns:
        MetaStrategyAgent实例
    """
    return MetaStrategyAgent(model=model)
