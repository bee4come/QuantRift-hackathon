"""
Prompt 模板管理
提供可重用的 Prompt 模板基类和工具函数
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import json


class PromptTemplate(ABC):
    """Prompt 模板基类"""

    @abstractmethod
    def build(self, **kwargs) -> str:
        """
        构建 prompt

        Args:
            **kwargs: 模板参数

        Returns:
            str: 完整的 prompt 文本
        """
        pass

    @staticmethod
    def format_json(data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
        """
        格式化 JSON 数据

        Args:
            data: 要格式化的数据
            indent: 缩进空格数
            ensure_ascii: 是否转义非 ASCII 字符

        Returns:
            str: 格式化后的 JSON 字符串
        """
        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)

    @staticmethod
    def truncate_list(items: List, max_items: int, suffix: str = "...") -> List:
        """
        截断列表

        Args:
            items: 列表
            max_items: 最大保留项数
            suffix: 截断后缀

        Returns:
            List: 截断后的列表
        """
        if len(items) <= max_items:
            return items
        return items[:max_items]


class PlayerAnalysisPromptTemplate(PromptTemplate):
    """玩家分析通用 Prompt 模板"""

    @staticmethod
    def build_header(
        patches: List[str],
        total_games: int,
        unique_champions: int
    ) -> str:
        """构建数据总览部分"""
        return f"""# 数据总览
- 版本范围: {patches[0]} - {patches[-1]} (共{len(patches)}个版本)
- 总比赛数: {total_games}场
- 使用英雄数: {unique_champions}个英雄-位置组合
"""

    @staticmethod
    def build_detailed_requirements(
        word_count: str = "8000-10000字",
        sections: Optional[List[str]] = None
    ) -> str:
        """构建详细报告要求"""
        default_sections = [
            "## 一、执行摘要 (500字)",
            "## 二、逐版本深度分析 (2000字)",
            "## 三、核心英雄全面剖析 (2500字)",
            "## 四、出装与符文深度解析 (1500字)",
            "## 五、Meta适应性评估 (1000字)",
            "## 六、数据驱动的战术建议 (1500字)",
            "## 七、未来版本展望 (500字)"
        ]

        sections_text = sections or default_sections

        return f"""
请生成一份**{word_count}**的超详细专业报告，必须包含以下内容：

{chr(10).join(sections_text)}

## 格式要求：
1. **必须使用中文**
2. **大量使用具体数据支撑所有结论**（胜率、KDA、场次、装备ID等）
3. **使用Markdown格式**，包括表格、列表、加粗、代码块
4. **每个观点必须有数据支撑**，不能泛泛而谈
5. **提供可执行的具体建议**，包括装备ID、英雄ID、版本号
6. **专业但易懂**，避免过度简化
7. **客观公正**，指出问题时要温和但明确
"""

    def build(
        self,
        data_package: Dict[str, Any],
        word_count: str = "8000-10000字",
        **kwargs
    ) -> str:
        """
        构建完整的玩家分析 prompt

        Args:
            data_package: 数据包（包含 overview, patch_analysis 等）
            word_count: 字数要求
            **kwargs: 其他参数

        Returns:
            str: 完整 prompt
        """
        overview = data_package.get("overview", {})
        patch_analysis = data_package.get("patch_by_patch_analysis", [])
        champion_deep_dive = data_package.get("champion_deep_dive", [])
        build_evolution = data_package.get("build_evolution", [])
        meta_alignment = data_package.get("meta_alignment", [])
        performance_metrics = data_package.get("performance_metrics", {})

        header = self.build_header(
            patches=overview.get("patches", []),
            total_games=overview.get("total_games", 0),
            unique_champions=overview.get("unique_champion_roles", 0)
        )

        requirements = self.build_detailed_requirements(word_count)

        prompt = f"""你是一名顶级的英雄联盟数据分析师和教练。基于以下超详细的数据，生成一份专业的深度分析报告。

{header}

# 逐版本详细数据
{self.format_json(patch_analysis)}

# 核心英雄深度分析 (Top 10)
{self.format_json(champion_deep_dive[:10])}

# 出装进化分析 (最近30条变化)
{self.format_json(build_evolution[-30:] if len(build_evolution) > 30 else build_evolution)}

# Meta对齐分析
{self.format_json(meta_alignment)}

# 综合表现指标
{self.format_json(performance_metrics)}

---

{requirements}

输出一份**完整、详细、专业**的报告。"""

        return prompt


class ComparisonPromptTemplate(PromptTemplate):
    """版本对比 Prompt 模板"""

    def build(
        self,
        comparison_data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        构建版本对比 prompt

        Args:
            comparison_data: 对比数据
            **kwargs: 其他参数

        Returns:
            str: 完整 prompt
        """
        prompt = f"""你是一名顶级的英雄联盟数据分析师。基于以下两个版本的对比数据，生成一份专业的Coach Card对比报告。

{self.format_json(comparison_data)}

请生成一份**详细的版本对比报告**，包含：

## 一、版本对比总览
- 整体表现变化
- 关键指标对比

## 二、英雄表现变化
- 表现提升的英雄
- 表现下滑的英雄
- 新增/放弃的英雄

## 三、Meta适应性分析
- Meta变化对个人表现的影响
- 成功适应的案例
- 失败适应的案例

## 四、具体改进建议
- 英雄池调整
- 出装优化
- 战术调整

输出一份**完整、客观、可操作**的Coach Card报告。"""

        return prompt
