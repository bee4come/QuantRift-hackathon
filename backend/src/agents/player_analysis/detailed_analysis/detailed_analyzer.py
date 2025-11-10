#!/usr/bin/env python3
"""
详细深度分析器 - 生成超详细的逐版本、逐英雄分析报告
使用Bedrock Claude Sonnet 4.5生成长篇深度报告
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import boto3
import os

class DetailedAnalyzer:
    def __init__(self, packs_dir: Path, meta_dir: Path):
        self.packs_dir = packs_dir
        self.meta_dir = meta_dir
        self.all_packs = {}
        self.all_meta = {}
        self.bedrock_runtime = None
        self._init_bedrock()

    def _init_bedrock(self):
        """初始化Bedrock客户端"""
        env_file = Path("/home/zty/rift_rewind/.env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key.startswith('AWS_'):
                            os.environ[key] = value

        from botocore.config import Config
        config = Config(
            read_timeout=600,
            connect_timeout=60,
            retries={'max_attempts': 3}
        )
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv("AWS_REGION", "us-west-2"),
            config=config
        )

    def load_all_data(self):
        """加载所有数据"""
        print("📦 加载所有数据...")

        # Load Player-Packs
        pack_files = sorted(self.packs_dir.glob("pack_*.json"))
        for pack_file in pack_files:
            patch = pack_file.stem.replace("pack_", "")
            with open(pack_file, 'r', encoding='utf-8') as f:
                self.all_packs[patch] = json.load(f)

        print(f"   ✅ 已加载 {len(self.all_packs)} 个版本的Player-Pack")

        # Load global meta files
        meta_files = list(self.meta_dir.glob("*.json"))
        for meta_file in meta_files:
            with open(meta_file, 'r', encoding='utf-8') as f:
                self.all_meta[meta_file.stem] = json.load(f)

        print(f"   ✅ 已加载 {len(self.all_meta)} 个全局Meta文件")

    def build_comprehensive_data_package(self) -> Dict[str, Any]:
        """构建超详细数据包"""
        print("🔍 构建超详细数据包...")

        package = {
            "overview": self._build_overview(),
            "patch_by_patch_analysis": self._build_patch_analysis(),
            "champion_deep_dive": self._build_champion_deep_dive(),
            "build_evolution": self._build_build_evolution(),
            "meta_alignment": self._build_meta_alignment(),
            "performance_metrics": self._build_performance_metrics()
        }

        print("   ✅ 超详细数据包构建完成")
        return package

    def _build_overview(self) -> Dict:
        """总览数据"""
        total_games = sum(pack["total_games"] for pack in self.all_packs.values())
        all_crs = set()
        for pack in self.all_packs.values():
            for cr in pack["by_cr"]:
                all_crs.add((cr["champ_id"], cr["role"]))

        return {
            "total_patches": len(self.all_packs),
            "total_games": total_games,
            "unique_champion_roles": len(all_crs),
            "patches": sorted(self.all_packs.keys())
        }

    def _build_patch_analysis(self) -> List[Dict]:
        """逐版本详细分析"""
        patch_data = []

        for patch in sorted(self.all_packs.keys()):
            pack = self.all_packs[patch]

            # 计算该版本的统计
            total_games = pack["total_games"]
            total_wins = sum(cr["wins"] for cr in pack["by_cr"])
            avg_kda = sum(cr["kda_adj"] for cr in pack["by_cr"]) / len(pack["by_cr"]) if pack["by_cr"] else 0
            avg_cp25 = sum(cr["cp_25"] for cr in pack["by_cr"]) / len(pack["by_cr"]) if pack["by_cr"] else 0

            # 最佳和最差英雄
            best_champs = sorted(
                [cr for cr in pack["by_cr"] if cr["games"] >= 3],
                key=lambda x: x["p_hat"],
                reverse=True
            )[:3]

            worst_champs = sorted(
                [cr for cr in pack["by_cr"] if cr["games"] >= 3],
                key=lambda x: x["p_hat"]
            )[:3]

            patch_data.append({
                "patch": patch,
                "total_games": total_games,
                "total_wins": total_wins,
                "overall_winrate": round(total_wins / total_games, 4) if total_games > 0 else 0,
                "avg_kda": round(avg_kda, 2),
                "avg_cp25": round(avg_cp25, 1),
                "champion_pool_size": len(pack["by_cr"]),
                "best_performers": best_champs,
                "worst_performers": worst_champs,
                "all_champion_roles": pack["by_cr"]
            })

        return patch_data

    def _build_champion_deep_dive(self) -> List[Dict]:
        """每个英雄的详细深度分析"""
        # 收集所有英雄-位置组合
        all_cr_stats = {}

        for patch in sorted(self.all_packs.keys()):
            pack = self.all_packs[patch]
            for cr in pack["by_cr"]:
                key = (cr["champ_id"], cr["role"])
                if key not in all_cr_stats:
                    all_cr_stats[key] = {
                        "champion_id": cr["champ_id"],
                        "role": cr["role"],
                        "patches": []
                    }

                all_cr_stats[key]["patches"].append({
                    "patch": patch,
                    "games": cr["games"],
                    "wins": cr["wins"],
                    "losses": cr["losses"],
                    "winrate": cr["p_hat"],
                    "winrate_ci": cr["p_hat_ci"],
                    "kda": cr["kda_adj"],
                    "obj_rate": cr["obj_rate"],
                    "cp_25": cr["cp_25"],
                    "build_core": cr["build_core"],
                    "rune_keystone": cr["rune_keystone"],
                    "effective_n": cr["effective_n"],
                    "governance_tag": cr["governance_tag"]
                })

        # 计算趋势
        champion_analysis = []
        for cr_key, stats in all_cr_stats.items():
            patches = stats["patches"]
            total_games = sum(p["games"] for p in patches)

            # 只分析至少玩了5场的英雄
            if total_games < 5:
                continue

            # 计算趋势
            winrates = [p["winrate"] for p in patches]
            wr_trend = "上升" if winrates[-1] > winrates[0] else "下降" if winrates[-1] < winrates[0] else "持平"
            wr_change = (winrates[-1] - winrates[0]) * 100

            # 最佳和最差版本
            best_patch = max(patches, key=lambda p: p["winrate"])
            worst_patch = min(patches, key=lambda p: p["winrate"])

            champion_analysis.append({
                "champion_id": stats["champion_id"],
                "role": stats["role"],
                "total_games": total_games,
                "total_patches": len(patches),
                "first_patch": patches[0]["patch"],
                "last_patch": patches[-1]["patch"],
                "winrate_trend": wr_trend,
                "winrate_change_pct": round(wr_change, 2),
                "best_patch": {
                    "patch": best_patch["patch"],
                    "winrate": best_patch["winrate"],
                    "games": best_patch["games"]
                },
                "worst_patch": {
                    "patch": worst_patch["patch"],
                    "winrate": worst_patch["winrate"],
                    "games": worst_patch["games"]
                },
                "patch_details": patches
            })

        # 按总场次排序
        champion_analysis.sort(key=lambda x: x["total_games"], reverse=True)
        return champion_analysis

    def _build_build_evolution(self) -> List[Dict]:
        """出装进化分析"""
        build_changes = []

        # 对每个连续版本对比较
        patches = sorted(self.all_packs.keys())
        for i in range(len(patches) - 1):
            patch_a = patches[i]
            patch_b = patches[i + 1]

            pack_a = self.all_packs[patch_a]
            pack_b = self.all_packs[patch_b]

            # 构建字典
            dict_a = {(cr["champ_id"], cr["role"]): cr for cr in pack_a["by_cr"]}
            dict_b = {(cr["champ_id"], cr["role"]): cr for cr in pack_b["by_cr"]}

            # 找共同英雄
            common_keys = set(dict_a.keys()) & set(dict_b.keys())

            for key in common_keys:
                cr_a = dict_a[key]
                cr_b = dict_b[key]

                items_a = set(cr_a["build_core"])
                items_b = set(cr_b["build_core"])

                if items_a != items_b:
                    build_changes.append({
                        "patch_transition": f"{patch_a} → {patch_b}",
                        "champion_id": key[0],
                        "role": key[1],
                        "items_removed": list(items_a - items_b),
                        "items_added": list(items_b - items_a),
                        "items_kept": list(items_a & items_b),
                        "winrate_before": cr_a["p_hat"],
                        "winrate_after": cr_b["p_hat"],
                        "winrate_change": round((cr_b["p_hat"] - cr_a["p_hat"]) * 100, 2)
                    })

        return build_changes

    def _build_meta_alignment(self) -> List[Dict]:
        """Meta对齐分析 - 玩家选择vs全局Meta"""
        alignment = []

        # 查找可用的delta_cp文件
        delta_cp_files = [k for k in self.all_meta.keys() if k.startswith("global_delta_cp")]

        for file_key in delta_cp_files:
            delta_cp_data = self.all_meta[file_key]

            # 提取版本
            parts = file_key.split("_")
            if len(parts) >= 5:
                patch_a = parts[3]
                patch_b = parts[4].replace(".json", "")

                if patch_a in self.all_packs and patch_b in self.all_packs:
                    pack_a = self.all_packs[patch_a]
                    pack_b = self.all_packs[patch_b]

                    # 构建delta_cp查找表
                    delta_cp_lookup = {
                        (entry["champion_id"], entry["role"]): entry["delta_cp_global"]
                        for entry in delta_cp_data.get("delta_cp_table", [])
                    }

                    # 分析玩家选择
                    dict_a = {(cr["champ_id"], cr["role"]): cr for cr in pack_a["by_cr"]}
                    dict_b = {(cr["champ_id"], cr["role"]): cr for cr in pack_b["by_cr"]}

                    common_keys = set(dict_a.keys()) & set(dict_b.keys())

                    for key in common_keys:
                        cr_a = dict_a[key]
                        cr_b = dict_b[key]
                        meta_z = delta_cp_lookup.get(key, 0.0)

                        wr_change = cr_b["p_hat"] - cr_a["p_hat"]

                        # 判断对齐情况
                        alignment_status = "未知"
                        if meta_z > 0.3 and wr_change > 0:
                            alignment_status = "完美对齐(英雄buff+表现提升)"
                        elif meta_z > 0.3 and wr_change < 0:
                            alignment_status = "逆势下滑(英雄buff但表现下降)"
                        elif meta_z < -0.3 and wr_change < 0:
                            alignment_status = "预期下滑(英雄nerf且表现下降)"
                        elif meta_z < -0.3 and wr_change > 0:
                            alignment_status = "逆势上升(英雄nerf但表现提升)"

                        alignment.append({
                            "patch_transition": f"{patch_a} → {patch_b}",
                            "champion_id": key[0],
                            "role": key[1],
                            "meta_z": round(meta_z, 2),
                            "winrate_change_pct": round(wr_change * 100, 2),
                            "alignment_status": alignment_status,
                            "games_before": cr_a["games"],
                            "games_after": cr_b["games"]
                        })

        return alignment

    def _build_performance_metrics(self) -> Dict:
        """综合表现指标"""
        metrics = {
            "by_patch": {},
            "overall": {}
        }

        # 逐版本指标
        for patch, pack in self.all_packs.items():
            total_games = pack["total_games"]
            total_wins = sum(cr["wins"] for cr in pack["by_cr"])
            avg_kda = sum(cr["kda_adj"] for cr in pack["by_cr"]) / len(pack["by_cr"]) if pack["by_cr"] else 0
            avg_cp25 = sum(cr["cp_25"] for cr in pack["by_cr"]) / len(pack["by_cr"]) if pack["by_cr"] else 0
            avg_obj_rate = sum(cr["obj_rate"] for cr in pack["by_cr"]) / len(pack["by_cr"]) if pack["by_cr"] else 0

            metrics["by_patch"][patch] = {
                "winrate": round(total_wins / total_games, 4) if total_games > 0 else 0,
                "kda": round(avg_kda, 2),
                "cp_25": round(avg_cp25, 1),
                "obj_rate": round(avg_obj_rate, 2)
            }

        # 总体指标
        total_games = sum(pack["total_games"] for pack in self.all_packs.values())
        total_wins = sum(sum(cr["wins"] for cr in pack["by_cr"]) for pack in self.all_packs.values())

        metrics["overall"] = {
            "total_games": total_games,
            "total_wins": total_wins,
            "overall_winrate": round(total_wins / total_games, 4) if total_games > 0 else 0
        }

        return metrics

    def generate_detailed_report(self, data_package: Dict[str, Any], model_name: str = "haiku") -> str:
        """使用Bedrock Claude生成超详细报告"""

        # 选择模型
        if model_name == "haiku":
            model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
            model_display = "Claude 3.5 Haiku"
            max_tokens = 8000
        else:  # sonnet
            model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
            model_display = "Claude Sonnet 4.5"
            max_tokens = 16000

        print(f"🤖 调用Bedrock {model_display}生成超详细报告...")

        prompt = self._build_detailed_prompt(data_package)

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())
            report = response_body['content'][0]['text']
            token_usage = response_body['usage']

            print(f"   ✅ 超详细报告生成完成")
            print(f"   Model: {model_display}")
            print(f"   Token usage: {token_usage}")

            return report, token_usage, model_name
        except Exception as e:
            print(f"   ⚠️  Bedrock调用失败: {e}")
            return ("# 报告生成失败\nBedrock调用出错", {"input_tokens": 0, "output_tokens": 0}, model_name)

    def _build_detailed_prompt(self, data_package: Dict[str, Any]) -> str:
        """构建超详细prompt"""

        # 提取关键数据
        overview = data_package["overview"]
        patch_analysis = data_package["patch_by_patch_analysis"]
        champion_deep_dive = data_package["champion_deep_dive"]
        build_evolution = data_package["build_evolution"]
        meta_alignment = data_package["meta_alignment"]
        performance_metrics = data_package["performance_metrics"]

        prompt = f"""你是一名顶级的英雄联盟数据分析师和教练。基于以下超详细的数据，生成一份专业的深度分析报告。

# 数据总览
- 版本范围: {overview['patches'][0]} - {overview['patches'][-1]} (共{overview['total_patches']}个版本)
- 总比赛数: {overview['total_games']}场
- 使用英雄数: {overview['unique_champion_roles']}个英雄-位置组合

# 逐版本详细数据
{json.dumps(patch_analysis, indent=2, ensure_ascii=False)}

# 核心英雄深度分析 (Top 10)
{json.dumps(champion_deep_dive[:10], indent=2, ensure_ascii=False)}

# 出装进化分析 (最近30条变化)
{json.dumps(build_evolution[-30:], indent=2, ensure_ascii=False)}

# Meta对齐分析
{json.dumps(meta_alignment, indent=2, ensure_ascii=False)}

# 综合表现指标
{json.dumps(performance_metrics, indent=2, ensure_ascii=False)}

---

请生成一份**8000-10000字**的超详细专业报告，必须包含以下内容：

## 一、执行摘要 (500字)
- 核心发现（3-5条）
- 整体适应能力评级
- 关键问题和机会

## 二、逐版本深度分析 (2000字)
**对每个版本进行详细分析**：
- 游戏量和活跃度变化
- 该版本的英雄选择策略
- 该版本的胜率表现
- 与前一版本的对比
- 该版本的亮点和问题

## 三、核心英雄全面剖析 (2500字)
**对每个主要英雄进行深度分析**：
- 跨版本表现轨迹（包含具体数据）
- 胜率波动的具体原因分析
- 出装变化及其效果
- 该英雄的优势版本和劣势版本
- 具体的调整建议（出装、符文、打法）

## 四、出装与符文深度解析 (1500字)
- 主要出装变化的详细分析
- 哪些装备调整是成功的
- 哪些装备调整是失败的
- 符文选择的优化建议
- 具体的装备搭配推荐

## 五、Meta适应性评估 (1000字)
- 玩家选择与全局Meta的对齐程度
- 逆势英雄分析（Meta削弱但个人表现提升）
- 顺势英雄分析（Meta增强且个人表现提升）
- 适应失败案例（Meta增强但个人表现下滑）

## 六、数据驱动的战术建议 (1500字)
- 英雄池调整方案（保留/优化/放弃/新增）
- 出装路线优化
- 游戏节奏建议（早期/中期/后期）
- 版本适应策略
- 训练重点

## 七、未来版本展望 (500字)
- 基于趋势的未来版本预测
- 推荐的准备方向
- 风险预警

## 格式要求：
1. **必须使用中文**
2. **大量使用具体数据支撑所有结论**（胜率、KDA、场次、装备ID等）
3. **使用Markdown格式**，包括表格、列表、加粗、代码块
4. **每个观点必须有数据支撑**，不能泛泛而谈
5. **提供可执行的具体建议**，包括装备ID、英雄ID、版本号
6. **专业但易懂**，避免过度简化
7. **客观公正**，指出问题时要温和但明确

输出一份**完整、详细、专业**的报告。"""

        return prompt

    def run(self, output_dir: Path, model_name: str = "haiku"):
        """运行完整流程"""
        print("=" * 60)
        print("🎯 超详细深度分析系统")
        print("=" * 60)

        # 1. 加载数据
        self.load_all_data()

        # 2. 构建数据包
        data_package = self.build_comprehensive_data_package()

        # 3. 保存数据包
        data_file = output_dir / "detailed_analysis_data.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data_package, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 详细数据包已保存: {data_file} ({data_file.stat().st_size / 1024:.2f} KB)")

        # 4. 生成LLM报告
        report, token_usage, model_used = self.generate_detailed_report(data_package, model_name)

        # 5. 保存报告（根据模型名称保存不同文件）
        if model_used == "haiku":
            report_file = output_dir / "detailed_report_haiku.md"
        else:
            report_file = output_dir / "detailed_report_sonnet.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 超详细报告已保存: {report_file}")
        print(f"   Token usage: {token_usage}")

        print("\n" + "=" * 60)
        print("✅ 超详细深度分析完成!")
        print("=" * 60)

        return data_package, report

def main():
    import sys

    packs_dir = Path("/home/zty/rift_rewind/test_agents/player_coach/packs")
    meta_dir = Path("/home/zty/rift_rewind/test_agents/player_coach/global_meta")
    output_dir = Path("/home/zty/rift_rewind/test_agents/player_coach/final_output")

    # 从命令行参数获取模型名称，默认为sonnet
    model_name = sys.argv[1] if len(sys.argv) > 1 else "sonnet"

    analyzer = DetailedAnalyzer(packs_dir, meta_dir)
    data_package, report = analyzer.run(output_dir, model_name=model_name)

if __name__ == "__main__":
    main()
