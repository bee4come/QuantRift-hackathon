#!/usr/bin/env python3
"""
Coach Card Generator - 整合Production系统工具
使用src/中的脚本分析所有版本变化，生成完整coach card并用LLM生成报告

流程:
1. 使用PatchQuantifier分析15.18→15.19的全局变化
2. 结合Player-Pack和delta_cp数据
3. 生成完整coach card (包含详细的build/rune分析)
4. 调用Bedrock生成文字报告
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import boto3
import os

sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import production系统工具
from src.core.patch_quantifier import PatchQuantifier


class CoachCardGenerator:
    """完整Coach Card生成器"""
    
    def __init__(self):
        self.patch_quantifier = None
        self.player_pack_t_minus_1 = None
        self.player_pack_t = None
        self.delta_cp_data = None
        self.item_changes = None
        self.rune_changes = None
        
        # Bedrock client
        self.bedrock_runtime = None
        self._init_bedrock()
    
    def _init_bedrock(self):
        """初始化Bedrock客户端"""
        # Load .env
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
        
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv("AWS_REGION", "us-west-2")
        )
    
    def load_all_data(self, packs_dir: Path, meta_dir: Path):
        """加载所有数据"""
        print("\n📦 加载所有数据...")
        
        # Load Player-Pack
        with open(packs_dir / "pack_15.18.json", 'r') as f:
            self.player_pack_t_minus_1 = json.load(f)
        with open(packs_dir / "pack_15.19.json", 'r') as f:
            self.player_pack_t = json.load(f)
        print(f"   ✅ Player-Pack: {len(self.player_pack_t_minus_1['by_cr'])} vs {len(self.player_pack_t['by_cr'])} champion-roles")
        
        # Load global meta
        with open(meta_dir / "global_delta_cp_15.18_15.19.json", 'r') as f:
            self.delta_cp_data = json.load(f)
        with open(meta_dir / "item_ge_changes_15.18_15.19.json", 'r') as f:
            self.item_changes = json.load(f)
        with open(meta_dir / "rune_value_changes_15.18_15.19.json", 'r') as f:
            self.rune_changes = json.load(f)
        print(f"   ✅ Global Meta: {len(self.delta_cp_data['delta_cp_table'])} champs, {len(self.item_changes['item_ge_changes'])} items, {len(self.rune_changes['rune_value_changes'])} runes")
    
    def generate_comprehensive_coach_card(self) -> Dict[str, Any]:
        """生成完整的coach card"""
        print("\n🎯 生成完整Coach Card...")
        
        # Build comprehensive card
        coach_card = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "patch_window": "15.18 → 15.19",
                "player_puuid": "9f7jpp6aurMHTFyM-sSWddoCP7SO0BxoSpYQvFICVr9_aF3hnZx1WrpY7aBlCuuhRp2rbK4peb67iA"
            },
            
            # 玩家表现数据
            "player_performance": {
                "patch_15_18": {
                    "total_games": self.player_pack_t_minus_1['total_games'],
                    "champion_roles": self.player_pack_t_minus_1['by_cr']
                },
                "patch_15_19": {
                    "total_games": self.player_pack_t['total_games'],
                    "champion_roles": self.player_pack_t['by_cr']
                }
            },
            
            # 全局Meta变化
            "global_meta_changes": {
                "delta_cp_summary": self.delta_cp_data['summary'],
                "top_buffed_champions": [
                    {"champ_id": e['champion_id'], "role": e['role'], "delta_cp": e['delta_cp_global']}
                    for e in self.delta_cp_data['delta_cp_table'] if e['category'] == 'buffed'
                ][:10],
                "top_nerfed_champions": [
                    {"champ_id": e['champion_id'], "role": e['role'], "delta_cp": e['delta_cp_global']}
                    for e in self.delta_cp_data['delta_cp_table'] if e['category'] == 'nerfed'
                ][:10],
                "item_changes_summary": {
                    "total_items_changed": len(self.item_changes['item_ge_changes']),
                    "top_buffed_items": self._get_top_items(buffed=True),
                    "top_nerfed_items": self._get_top_items(buffed=False)
                },
                "rune_changes_summary": {
                    "total_runes_changed": len(self.rune_changes['rune_value_changes']),
                    "changes": self.rune_changes['rune_value_changes']
                }
            },
            
            # 玩家适配分析
            "adaptation_analysis": self._analyze_player_adaptation(),
            
            # 关键建议
            "key_recommendations": self._generate_recommendations()
        }
        
        print(f"   ✅ Coach Card生成完成")
        return coach_card
    
    def _get_top_items(self, buffed: bool = True, n: int = 5) -> List[Dict]:
        """获取top buffed/nerfed items"""
        items = []
        for item_id, delta_ge in self.item_changes['item_ge_changes'].items():
            if (buffed and delta_ge > 0) or (not buffed and delta_ge < 0):
                items.append({"item_id": int(item_id), "delta_ge": delta_ge})
        
        items.sort(key=lambda x: abs(x['delta_ge']), reverse=True)
        return items[:n]
    
    def _analyze_player_adaptation(self) -> Dict[str, Any]:
        """分析玩家适配情况"""
        adaptation = {
            "champion_pool_changes": [],
            "build_adaptation": [],
            "rune_adaptation": []
        }
        
        # Build dictionaries
        pack_t_minus_1_dict = {(e['champ_id'], e['role']): e for e in self.player_pack_t_minus_1['by_cr']}
        pack_t_dict = {(e['champ_id'], e['role']): e for e in self.player_pack_t['by_cr']}
        
        # Delta CP lookup
        delta_cp_lookup = {(e['champion_id'], e['role']): e['delta_cp_global'] 
                          for e in self.delta_cp_data['delta_cp_table']}
        
        # Analyze common champions
        common_keys = set(pack_t_minus_1_dict.keys()) & set(pack_t_dict.keys())
        
        for key in common_keys:
            champ_id, role = key
            stats_before = pack_t_minus_1_dict[key]
            stats_after = pack_t_dict[key]
            
            # Champion performance change
            wr_change = stats_after['p_hat'] - stats_before['p_hat']
            meta_z = delta_cp_lookup.get(key, 0.0)
            
            adaptation["champion_pool_changes"].append({
                "champ_id": champ_id,
                "role": role,
                "wr_before": stats_before['p_hat'],
                "wr_after": stats_after['p_hat'],
                "wr_change": round(wr_change, 4),
                "meta_z": round(meta_z, 4),
                "games_before": stats_before['games'],
                "games_after": stats_after['games']
            })
            
            # Build changes
            items_before = set(stats_before['build_core'])
            items_after = set(stats_after['build_core'])
            items_added = list(items_after - items_before)
            items_removed = list(items_before - items_after)
            
            if items_added or items_removed:
                adaptation["build_adaptation"].append({
                    "champ_id": champ_id,
                    "role": role,
                    "items_added": items_added,
                    "items_removed": items_removed,
                    "items_added_impact": sum(float(self.item_changes['item_ge_changes'].get(str(i), 0)) for i in items_added),
                    "items_removed_impact": sum(float(self.item_changes['item_ge_changes'].get(str(i), 0)) for i in items_removed)
                })
            
            # Rune changes
            if stats_before['rune_keystone'] != stats_after['rune_keystone']:
                adaptation["rune_adaptation"].append({
                    "champ_id": champ_id,
                    "role": role,
                    "rune_before": stats_before['rune_keystone'],
                    "rune_after": stats_after['rune_keystone'],
                    "rune_impact": float(self.rune_changes['rune_value_changes'].get(str(stats_after['rune_keystone']), 0))
                })
        
        return adaptation
    
    def _generate_recommendations(self) -> List[Dict]:
        """生成关键建议"""
        recommendations = []
        
        adaptation = self._analyze_player_adaptation()
        
        # Analyze each champion
        for champ_change in adaptation['champion_pool_changes']:
            champ_id = champ_change['champ_id']
            role = champ_change['role']
            wr_change = champ_change['wr_change']
            meta_z = champ_change['meta_z']
            
            if wr_change < 0 and meta_z < -0.35:
                # 双重劣势: 表现下滑 + 英雄被nerf
                recommendations.append({
                    "priority": "high",
                    "category": "swap",
                    "champ_id": champ_id,
                    "role": role,
                    "message": f"Champion {champ_id} ({role}): 表现下降 ({wr_change:+.2%}) + 英雄被削弱 (meta_z={meta_z:.2f}), 建议考虑更换英雄池"
                })
            elif wr_change < 0 and meta_z >= 0:
                # 英雄正常/被buff但表现下滑: 需要调整打法/build
                recommendations.append({
                    "priority": "medium",
                    "category": "retune",
                    "champ_id": champ_id,
                    "role": role,
                    "message": f"Champion {champ_id} ({role}): 表现下降 ({wr_change:+.2%}) 但英雄未被削弱, 建议调整出装或打法"
                })
            elif wr_change >= 0 and meta_z >= 0.35:
                # 表现进步 + 英雄被buff: 继续保持
                recommendations.append({
                    "priority": "low",
                    "category": "keep",
                    "champ_id": champ_id,
                    "role": role,
                    "message": f"Champion {champ_id} ({role}): 表现提升 ({wr_change:+.2%}) + 英雄被增强 (meta_z={meta_z:.2f}), 继续使用该英雄"
                })
        
        return recommendations
    
    def generate_llm_report(self, coach_card: Dict[str, Any], output_file: Path) -> str:
        """使用Bedrock LLM生成文字报告"""
        print("\n🤖 生成LLM报告...")
        
        # Prepare compact prompt
        prompt = self._build_llm_prompt(coach_card)
        
        # Call Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.bedrock_runtime.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        report_text = response_body['content'][0]['text']
        
        # Save report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"   ✅ LLM报告已保存: {output_file}")
        print(f"   Token usage: {response_body['usage']}")
        
        return report_text
    
    def _build_llm_prompt(self, coach_card: Dict[str, Any]) -> str:
        """构建LLM prompt"""
        return f"""你是一名专业的英雄联盟教练。根据以下数据生成一份专业的版本适配报告。

## 版本窗口
{coach_card['metadata']['patch_window']}

## 玩家表现总览
### 15.18版本
- 总场次: {coach_card['player_performance']['patch_15_18']['total_games']}
- 使用英雄数: {len(coach_card['player_performance']['patch_15_18']['champion_roles'])}

### 15.19版本
- 总场次: {coach_card['player_performance']['patch_15_19']['total_games']}
- 使用英雄数: {len(coach_card['player_performance']['patch_15_19']['champion_roles'])}

## 全局Meta变化
### Delta CP Summary
- Buffed英雄: {coach_card['global_meta_changes']['delta_cp_summary']['buffed']}
- Nerfed英雄: {coach_card['global_meta_changes']['delta_cp_summary']['nerfed']}
- 中性英雄: {coach_card['global_meta_changes']['delta_cp_summary']['neutral']}

### 装备变化
- 变化装备数: {coach_card['global_meta_changes']['item_changes_summary']['total_items_changed']}
- Top Buffed: {json.dumps(coach_card['global_meta_changes']['item_changes_summary']['top_buffed_items'][:3], ensure_ascii=False)}
- Top Nerfed: {json.dumps(coach_card['global_meta_changes']['item_changes_summary']['top_nerfed_items'][:3], ensure_ascii=False)}

## 玩家适配分析
{json.dumps(coach_card['adaptation_analysis'], indent=2, ensure_ascii=False)}

## 关键建议
{json.dumps(coach_card['key_recommendations'], indent=2, ensure_ascii=False)}

请生成一份1000-1500字的专业报告，包含:
1. **版本变化总结** - 15.18→15.19的主要Meta变化
2. **玩家表现分析** - 玩家在两个版本中的表现变化及原因
3. **装备与符文建议** - 具体的出装和符文调整建议
4. **英雄池规划** - 哪些英雄应该继续使用，哪些需要调整或更换
5. **训练重点** - 针对性的训练建议

要求:
- 使用专业但易懂的语言
- 所有结论必须基于数据
- 提供可执行的具体建议
- 中文输出"""
    
    def run(self, packs_dir: Path, meta_dir: Path, output_dir: Path):
        """运行完整流程"""
        print("=" * 60)
        print("🏆 Coach Card Generator - Complete System")
        print("=" * 60)
        
        # Load data
        self.load_all_data(packs_dir, meta_dir)
        
        # Generate coach card
        coach_card = self.generate_comprehensive_coach_card()
        
        # Save coach card
        card_file = output_dir / "complete_coach_card_15.18_15.19.json"
        with open(card_file, 'w', encoding='utf-8') as f:
            json.dump(coach_card, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Coach Card已保存: {card_file}")
        print(f"   大小: {card_file.stat().st_size / 1024:.2f} KB")
        
        # Generate LLM report
        report_file = output_dir / "coaching_report_15.18_15.19.md"
        report_text = self.generate_llm_report(coach_card, report_file)
        
        print("\n" + "=" * 60)
        print("✅ 完整Coach Card和报告生成完成")
        print("=" * 60)
        print(f"\n📁 输出文件:")
        print(f"   - Coach Card: {card_file}")
        print(f"   - LLM Report: {report_file}")
        
        return coach_card, report_text


def main():
    """主程序"""
    packs_dir = Path("/home/zty/rift_rewind/test_agents/player_coach/packs")
    meta_dir = Path("/home/zty/rift_rewind/test_agents/player_coach/global_meta")
    output_dir = Path("/home/zty/rift_rewind/test_agents/player_coach/final_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = CoachCardGenerator()
    coach_card, report = generator.run(packs_dir, meta_dir, output_dir)


if __name__ == "__main__":
    main()
