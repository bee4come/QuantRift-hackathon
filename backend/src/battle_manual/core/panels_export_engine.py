#!/usr/bin/env python3
"""
Quantitative Panels Export Engine

Implements Battle Manual Step 6: Priority implementation and export triple:
- entity_panel.jsonl (≤3k rows, CONFIDENT priority) 
- context_panel.jsonl (CAUTION/CONTEXT for research)
- patch_summary.jsonl (patch-level aggregated insights)

Generates "universal, interpretable, traceable" quantitative panels for:
- Version comparison
- Combo discovery  
- User reports
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from collections import defaultdict

from core_metrics_engine import CoreMetricsEngine, MetricResult

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class EntityPanelRecord:
    """Standard record structure for entity panel (production-ready insights)."""
    # Entity identifiers (unified grain)
    patch_version: str
    champion: str
    role: str
    entity_type: str  # 'hero' or 'combo'
    
    # Combo-specific fields (null for hero entities)
    core_items_3: Optional[str] = None
    rune_page: Optional[str] = None
    spell_pair: Optional[str] = None
    
    # Core metrics (immediate priority)
    pick_rate: float = 0.0
    winrate: float = 0.0
    winrate_ci_lo: float = 0.0  
    winrate_ci_hi: float = 0.0
    winrate_delta_vs_baseline: float = 0.0
    
    # Performance metrics
    kda_adj: float = 0.0
    dpm: float = 0.0
    obj_rate: float = 0.0
    avg_time_to_core: Optional[float] = None
    
    # Advanced metrics (day 1 priority)
    cp_25: Optional[float] = None
    delta_cp: Optional[float] = None
    item_ge_25: Optional[float] = None
    rune_value_25: Optional[float] = None
    
    # Governance (mandatory Battle Manual fields)
    n: int = 0
    effective_n: float = 0.0
    governance_tag: str = "CONTEXT"  # CONFIDENT/CAUTION/CONTEXT
    uses_prior: bool = True
    metric_version: str = "efp_v1.0"
    generated_at: str = ""
    plus_one_patch_buffer: bool = True
    data_quality_score: float = 0.0
    aggregation_level: str = "entity"
    
    # Meta analysis
    meta_strength_score: Optional[float] = None  # Composite strength indicator
    combo_viability_score: Optional[float] = None  # For combo entities only
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


@dataclass  
class ContextPanelRecord:
    """Research-focused record for context panel (broader analysis)."""
    # Entity identifiers
    patch_version: str
    entity_id: str  # Unique identifier for this analysis
    analysis_type: str  # 'low_sample', 'experimental', 'trend_analysis', etc
    
    # Flexible metrics container
    metrics: Dict[str, Any]  # All available metrics
    
    # Research metadata
    sample_size: int
    confidence_level: str  # CAUTION/CONTEXT
    research_notes: str
    limitations: List[str]
    
    # Governance
    metric_version: str = "efp_v1.0"
    generated_at: str = ""
    aggregation_level: str = "context"
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class PatchSummaryRecord:
    """Patch-level aggregated insights for version comparison."""
    patch_version: str
    
    # Meta overview
    total_entities_analyzed: int
    total_games_processed: int
    avg_data_quality_score: float
    confident_entities_count: int
    
    # Patch-level metrics
    overall_game_duration_avg: float
    overall_kill_rate: float
    patch_shock_score: Optional[float] = None
    
    # Meta strength leaders
    strongest_champions: List[Dict[str, Any]]  # Top 10 by cp_25 + delta_cp
    biggest_winners: List[Dict[str, Any]]      # Top 10 winrate gains
    biggest_losers: List[Dict[str, Any]]       # Top 10 winrate losses
    
    # Role meta summary
    role_meta_summary: Dict[str, Dict[str, Any]]  # Per-role insights
    
    # Build meta insights
    trending_items: List[Dict[str, Any]]      # Item efficiency + pick rate changes
    trending_runes: List[Dict[str, Any]]      # Rune value + usage changes
    optimal_combos: List[Dict[str, Any]]      # Highest viability combos
    
    # Governance
    metric_version: str = "efp_v1.0"
    generated_at: str = ""
    aggregation_level: str = "patch"
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


class PanelsExportEngine:
    """
    Export engine for the three Battle Manual quantitative panels.
    
    Processes metric results from CoreMetricsEngine and generates:
    1. Entity Panel: Production insights (≤3k rows, CONFIDENT priority)
    2. Context Panel: Research insights (broader, CAUTION/CONTEXT)  
    3. Patch Summary: Aggregated version comparison insights
    """
    
    def __init__(self, output_dir: str = "output/"):
        """Initialize export engine."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Panel configurations
        self.entity_panel_max_rows = 3000
        self.priority_metrics = [
            'pick_rate', 'winrate', 'winrate_delta_vs_baseline',
            'kda_adj', 'dpm', 'obj_rate', 'avg_time_to_core'
        ]
        
        # Export statistics
        self.export_stats = {
            'entity_panel_records': 0,
            'context_panel_records': 0,
            'patches_summarized': 0,
            'total_metrics_processed': 0
        }
        
    def export_all_panels(self, metrics_results: Dict[str, Dict[str, List[MetricResult]]], 
                         match_data: Dict[str, List[Dict]]) -> Dict[str, str]:
        """
        Export all three quantitative panels from metric results.
        
        Args:
            metrics_results: Results from CoreMetricsEngine by patch and category
            match_data: Original match data by patch for aggregation
            
        Returns:
            Dictionary with paths to exported panel files
        """
        logger.info("Starting quantitative panels export...")
        
        export_paths = {}
        
        # Generate and export entity panel
        logger.info("Generating entity panel...")
        entity_records = self._generate_entity_panel(metrics_results)
        export_paths['entity_panel'] = self._export_jsonl(
            entity_records, 'entity_panel.jsonl', EntityPanelRecord
        )
        
        # Generate and export context panel
        logger.info("Generating context panel...")
        context_records = self._generate_context_panel(metrics_results)
        export_paths['context_panel'] = self._export_jsonl(
            context_records, 'context_panel.jsonl', ContextPanelRecord
        )
        
        # Generate and export patch summary
        logger.info("Generating patch summary...")
        patch_records = self._generate_patch_summary(metrics_results, match_data)
        export_paths['patch_summary'] = self._export_jsonl(
            patch_records, 'patch_summary.jsonl', PatchSummaryRecord
        )
        
        # Export summary report
        summary_report = self._generate_export_summary(export_paths)
        summary_path = self.output_dir / 'panels_export_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary_report, f, indent=2)
        export_paths['export_summary'] = str(summary_path)
        
        logger.info(f"Panel export completed. Files: {list(export_paths.keys())}")
        return export_paths
        
    def _generate_entity_panel(self, metrics_results: Dict) -> List[EntityPanelRecord]:
        """
        Generate entity panel (≤3k rows, CONFIDENT priority).
        
        Priority order:
        1. CONFIDENT governance_tag
        2. Highest pick_rate (popularity)
        3. Highest winrate_delta_vs_baseline (impact)
        4. Role diversity (ensure all roles represented)
        """
        logger.info("Generating entity panel records...")
        entity_records = []
        
        for patch_version, categories in metrics_results.items():
            patch_entities = []
            
            # Process hero layer entities
            hero_entities = self._process_hero_layer_entities(categories, patch_version)
            patch_entities.extend(hero_entities)
            
            # Process combo layer entities  
            combo_entities = self._process_combo_layer_entities(categories, patch_version)
            patch_entities.extend(combo_entities)
            
            # Apply priority filtering and ranking
            prioritized_entities = self._prioritize_entities(patch_entities)
            entity_records.extend(prioritized_entities)
            
        # Final filtering to ensure ≤3k rows
        final_entities = self._apply_final_entity_filtering(entity_records)
        
        self.export_stats['entity_panel_records'] = len(final_entities)
        logger.info(f"Generated {len(final_entities)} entity panel records")
        
        return final_entities
        
    def _process_hero_layer_entities(self, categories: Dict, patch_version: str) -> List[EntityPanelRecord]:
        """Process hero layer (champion, role, patch) entities."""
        entities = []
        
        # Group metrics by champion+role
        hero_metrics = defaultdict(dict)
        
        for category_name, metric_results in categories.items():
            for metric in metric_results:
                if isinstance(metric, MetricResult):
                    # Extract champion and role from metric name
                    # Format: "{metric_type}_{champion}_{role}"
                    parts = metric.metric_name.split('_')
                    if len(parts) >= 3:
                        champion = parts[-2] 
                        role = parts[-1]
                        key = f"{champion}_{role}"
                        hero_metrics[key][category_name] = metric
                        
        # Convert to EntityPanelRecord
        for hero_key, metrics in hero_metrics.items():
            champion, role = hero_key.split('_', 1)
            
            # Only include CONFIDENT entities for entity panel
            winrate_metric = metrics.get('winrate_robustness')
            if not winrate_metric or winrate_metric.governance_tag != 'CONFIDENT':
                continue
                
            entity = EntityPanelRecord(
                patch_version=patch_version,
                champion=champion,
                role=role,
                entity_type='hero',
                
                # Extract core metrics from results
                winrate=winrate_metric.value if winrate_metric else 0.0,
                winrate_ci_lo=winrate_metric.ci_lo if winrate_metric else 0.0,
                winrate_ci_hi=winrate_metric.ci_hi if winrate_metric else 0.0,
                
                # Governance from winrate metric (highest quality)
                n=winrate_metric.n if winrate_metric else 0,
                effective_n=winrate_metric.effective_n if winrate_metric else 0.0,
                governance_tag=winrate_metric.governance_tag if winrate_metric else 'CONTEXT',
                uses_prior=winrate_metric.uses_prior if winrate_metric else True,
                data_quality_score=winrate_metric.data_quality_score if winrate_metric else 0.0
            )
            
            # Calculate meta strength score (composite)
            entity.meta_strength_score = self._calculate_meta_strength_score(entity)
            
            entities.append(entity)
            
        return entities
        
    def _process_combo_layer_entities(self, categories: Dict, patch_version: str) -> List[EntityPanelRecord]:
        """Process combo layer entities (champion+role+items+runes+spells).""" 
        # For MVP, return empty list - combo layer requires more complex grouping
        # In production, this would process combo-specific metrics
        return []
        
    def _prioritize_entities(self, entities: List[EntityPanelRecord]) -> List[EntityPanelRecord]:
        """Apply priority ranking to entities."""
        # Sort by priority criteria
        def priority_score(entity):
            governance_score = {'CONFIDENT': 100, 'CAUTION': 50, 'CONTEXT': 10}[entity.governance_tag]
            popularity_score = entity.pick_rate * 10
            impact_score = abs(entity.winrate_delta_vs_baseline) * 20
            quality_score = entity.data_quality_score * 5
            
            return governance_score + popularity_score + impact_score + quality_score
            
        return sorted(entities, key=priority_score, reverse=True)
        
    def _apply_final_entity_filtering(self, entities: List[EntityPanelRecord]) -> List[EntityPanelRecord]:
        """Apply final filtering to ensure ≤3k rows with role diversity."""
        if len(entities) <= self.entity_panel_max_rows:
            return entities
            
        # Ensure role diversity in final selection
        roles = ['ADC', 'MID', 'JUNGLE', 'TOP', 'SUPPORT']
        per_role_limit = self.entity_panel_max_rows // len(roles)
        
        final_entities = []
        for role in roles:
            role_entities = [e for e in entities if e.role == role][:per_role_limit]
            final_entities.extend(role_entities)
            
        return final_entities[:self.entity_panel_max_rows]
        
    def _generate_context_panel(self, metrics_results: Dict) -> List[ContextPanelRecord]:
        """Generate context panel for research insights (CAUTION/CONTEXT entities)."""
        logger.info("Generating context panel records...")
        context_records = []
        
        for patch_version, categories in metrics_results.items():
            # Process all non-CONFIDENT metrics for research
            for category_name, metric_results in categories.items():
                for metric in metric_results:
                    if isinstance(metric, MetricResult) and metric.governance_tag in ['CAUTION', 'CONTEXT']:
                        
                        context_record = ContextPanelRecord(
                            patch_version=patch_version,
                            entity_id=metric.metric_name,
                            analysis_type=f"{category_name}_{metric.governance_tag.lower()}",
                            
                            # Store all metric data for research
                            metrics={
                                'value': metric.value,
                                'n': metric.n,
                                'effective_n': metric.effective_n,
                                'ci_lo': metric.ci_lo,
                                'ci_hi': metric.ci_hi,
                                'data_quality_score': metric.data_quality_score
                            },
                            
                            sample_size=metric.n,
                            confidence_level=metric.governance_tag,
                            research_notes=f"Lower confidence {category_name} metric for research purposes",
                            limitations=['Small sample size', 'Lower statistical confidence']
                        )
                        
                        context_records.append(context_record)
                        
        self.export_stats['context_panel_records'] = len(context_records)
        logger.info(f"Generated {len(context_records)} context panel records")
        
        return context_records
        
    def _generate_patch_summary(self, metrics_results: Dict, match_data: Dict) -> List[PatchSummaryRecord]:
        """Generate patch-level summary insights."""
        logger.info("Generating patch summary records...")
        patch_records = []
        
        for patch_version in metrics_results.keys():
            # Aggregate patch-level statistics
            patch_matches = match_data.get(patch_version, [])
            total_games = len(patch_matches)
            
            # Calculate patch-level aggregates
            avg_duration = np.mean([m.get('game_duration_minutes', 30) for m in patch_matches]) if patch_matches else 30.0
            avg_kills = np.mean([m.get('kills', 5) for m in patch_matches]) if patch_matches else 5.0
            
            # Count entity analysis
            all_metrics = []
            for categories in metrics_results[patch_version].values():
                all_metrics.extend(categories)
                
            confident_count = len([m for m in all_metrics if hasattr(m, 'governance_tag') and m.governance_tag == 'CONFIDENT'])
            avg_quality = np.mean([m.data_quality_score for m in all_metrics if hasattr(m, 'data_quality_score')]) if all_metrics else 0.0
            
            patch_record = PatchSummaryRecord(
                patch_version=patch_version,
                total_entities_analyzed=len(all_metrics),
                total_games_processed=total_games,
                avg_data_quality_score=avg_quality,
                confident_entities_count=confident_count,
                overall_game_duration_avg=avg_duration,
                overall_kill_rate=avg_kills,
                
                # Placeholder leaders (would be calculated from actual data)
                strongest_champions=[],
                biggest_winners=[], 
                biggest_losers=[],
                role_meta_summary={},
                trending_items=[],
                trending_runes=[],
                optimal_combos=[]
            )
            
            patch_records.append(patch_record)
            
        self.export_stats['patches_summarized'] = len(patch_records)
        logger.info(f"Generated {len(patch_records)} patch summary records")
        
        return patch_records
        
    def _calculate_meta_strength_score(self, entity: EntityPanelRecord) -> float:
        """Calculate composite meta strength score."""
        # Composite score: winrate impact + popularity + data quality
        winrate_component = entity.winrate_delta_vs_baseline * 50  # Scale to reasonable range
        popularity_component = entity.pick_rate * 20
        quality_component = entity.data_quality_score * 10
        
        return winrate_component + popularity_component + quality_component
        
    def _export_jsonl(self, records: List, filename: str, record_class) -> str:
        """Export records to JSONL format."""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            for record in records:
                if hasattr(record, '__dict__'):
                    # Convert dataclass to dict
                    record_dict = asdict(record) if hasattr(record, '__dataclass_fields__') else record.__dict__
                else:
                    record_dict = record
                    
                f.write(json.dumps(record_dict, default=str) + '\n')
                
        logger.info(f"Exported {len(records)} records to {output_path}")
        return str(output_path)
        
    def _generate_export_summary(self, export_paths: Dict[str, str]) -> Dict[str, Any]:
        """Generate comprehensive export summary."""
        return {
            'battle_manual_panels_export': {
                'version': '1.0',
                'export_timestamp': datetime.now(timezone.utc).isoformat(),
                'files_generated': export_paths,
                'export_statistics': self.export_stats,
                'panel_specifications': {
                    'entity_panel': {
                        'purpose': 'Production insights for downstream consumers',
                        'max_rows': self.entity_panel_max_rows,
                        'governance_filter': 'CONFIDENT priority',
                        'record_type': 'EntityPanelRecord'
                    },
                    'context_panel': {
                        'purpose': 'Research insights for analysis and exploration',
                        'governance_filter': 'CAUTION/CONTEXT included',
                        'record_type': 'ContextPanelRecord'
                    },
                    'patch_summary': {
                        'purpose': 'Version comparison and meta overview',
                        'aggregation_level': 'patch',
                        'record_type': 'PatchSummaryRecord'
                    }
                },
                'battle_manual_compliance': {
                    'unified_grain': True,
                    'mandatory_governance_fields': True,
                    'wilson_confidence_intervals': True,
                    'effective_sample_size_calculation': True,
                    'evidence_quality_classification': True
                }
            }
        }


if __name__ == "__main__":
    # Example usage
    export_engine = PanelsExportEngine()
    
    # Mock results for testing
    mock_results = {
        '25.18': {
            'winrate_robustness': [
                MetricResult(
                    metric_name='winrate_Jinx_ADC',
                    value=0.52,
                    n=150,
                    effective_n=150.0,
                    ci_lo=0.48,
                    ci_hi=0.56,
                    governance_tag='CONFIDENT',
                    uses_prior=False,
                    data_quality_score=0.95
                )
            ]
        }
    }
    
    mock_match_data = {
        '25.18': [{'game_duration_minutes': 28, 'kills': 6}]
    }
    
    paths = export_engine.export_all_panels(mock_results, mock_match_data)
    print(f"Panels export test completed. Generated files: {list(paths.keys())}")