#!/usr/bin/env python3
"""
Quant Pack v1.0 Export System
Purpose: Generate standard JSONL packages for downstream agent consumption
Schema: Uses schema/metrics/efp_v1.yaml with 15 mandatory fields
Output Files: entity_panel.jsonl, context_panel.jsonl, patch_summary.jsonl
Governance: CONFIDENT priority, CAUTION secondary, ≤3K rows optimized
"""

import pandas as pd
import numpy as np
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime
import gzip
from dataclasses import dataclass

# Import our evidence and leakage prevention modules
import sys
sys.path.append('/home/zty/rift_rewind/experiment')
from metrics.utils.evidence_metadata import EvidenceStandardizer, EvidenceMetadata
from metrics.utils.leakage_prevention import LeakageGuard
from metrics.shock.shock_analysis import ShockAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExportConfig:
    """Configuration for Quant Pack export"""
    max_records_per_file: int = 3000
    governance_priority: List[str] = None
    compress_output: bool = False
    include_shock_indicators: bool = True
    include_evidence_metadata: bool = True
    leakage_buffer_patches: int = 1
    
    def __post_init__(self):
        if self.governance_priority is None:
            self.governance_priority = ["CONFIDENT", "CAUTION", "CONTEXT"]

class QuantPackExporter:
    """
    Quantitative Pack Export Engine
    Generates standardized JSONL packages for universal agent consumption
    """
    
    def __init__(self, schema_path: str = "schema/metrics/efp_v1.yaml", 
                 config: ExportConfig = None):
        """Initialize exporter with schema and configuration"""
        self.schema = self._load_schema(schema_path)
        self.config = config or ExportConfig()
        
        # Initialize utility engines
        self.evidence_standardizer = EvidenceStandardizer("efp_v1.0")
        self.leakage_guard = LeakageGuard(buffer_patches=self.config.leakage_buffer_patches)
        self.shock_analyzer = ShockAnalyzer()
        
        # Track export metadata
        self.export_metadata = {
            'export_version': 'quant_pack_v1.0',
            'schema_version': 'efp_v1.0',
            'generated_at': datetime.now().isoformat(),
            'total_records_processed': 0,
            'files_generated': []
        }
    
    def _load_schema(self, schema_path: str) -> Dict[str, Any]:
        """Load EFP schema definition"""
        try:
            with open(schema_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Schema file not found: {schema_path}, using minimal schema")
            return self._get_minimal_schema()
    
    def _get_minimal_schema(self) -> Dict[str, Any]:
        """Minimal schema if file not found"""
        return {
            'metadata': {
                'schema_name': 'efp_v1',
                'schema_version': '1.0'
            },
            'evidence_fields': {
                'n': {'type': 'integer', 'required': True},
                'effective_n': {'type': 'integer', 'required': True},
                'uses_prior': {'type': 'boolean', 'required': True},
                'ci_lo': {'type': 'number', 'required': True},
                'ci_hi': {'type': 'number', 'required': True},
                'metric_version': {'type': 'string', 'required': True},
                'generated_at': {'type': 'string', 'required': True}
            }
        }
    
    def validate_record_compliance(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate record against EFP v1.0 schema"""
        validation_result = {
            'is_compliant': True,
            'missing_fields': [],
            'type_errors': [],
            'constraint_violations': []
        }
        
        # Check mandatory evidence fields
        evidence_fields = self.schema.get('evidence_fields', {})
        quality_fields = self.schema.get('quality_fields', {})
        entity_fields = self.schema.get('entity_fields', {})
        value_fields = self.schema.get('value_fields', {})
        
        all_required_fields = {**evidence_fields, **quality_fields, **entity_fields, **value_fields}
        
        for field_name, field_spec in all_required_fields.items():
            if field_spec.get('required', False):
                if field_name not in record:
                    validation_result['missing_fields'].append(field_name)
                    validation_result['is_compliant'] = False
                else:
                    # Type validation
                    expected_type = field_spec.get('type')
                    actual_value = record[field_name]
                    
                    if expected_type == 'integer' and not isinstance(actual_value, int):
                        validation_result['type_errors'].append(f"{field_name}: expected int, got {type(actual_value)}")
                        validation_result['is_compliant'] = False
                    elif expected_type == 'number' and not isinstance(actual_value, (int, float)):
                        validation_result['type_errors'].append(f"{field_name}: expected number, got {type(actual_value)}")
                        validation_result['is_compliant'] = False
                    elif expected_type == 'boolean' and not isinstance(actual_value, bool):
                        validation_result['type_errors'].append(f"{field_name}: expected bool, got {type(actual_value)}")
                        validation_result['is_compliant'] = False
                    elif expected_type == 'string' and not isinstance(actual_value, str):
                        validation_result['type_errors'].append(f"{field_name}: expected str, got {type(actual_value)}")
                        validation_result['is_compliant'] = False
        
        # Check logical constraints
        if 'ci_lo' in record and 'ci_hi' in record:
            if record['ci_lo'] >= record['ci_hi']:
                validation_result['constraint_violations'].append("ci_lo must be less than ci_hi")
                validation_result['is_compliant'] = False
        
        if 'n' in record and 'effective_n' in record and not record.get('uses_prior', False):
            if record['effective_n'] < record['n']:
                validation_result['constraint_violations'].append("effective_n cannot be less than n without prior")
                validation_result['is_compliant'] = False
        
        return validation_result
    
    def standardize_metric_record(self, record: Dict[str, Any], 
                                metric_type: str, training_patch: str) -> Dict[str, Any]:
        """
        Standardize a metric record to EFP v1.0 compliance
        """
        # Step 1: Add evidence metadata if missing
        if not all(field in record for field in ['n', 'effective_n', 'uses_prior', 'ci_lo', 'ci_hi']):
            record = self.evidence_standardizer.standardize_metric_record(record, metric_type)
        
        # Step 2: Add leakage prevention if missing
        if 'leakage_guard' not in record or not record['leakage_guard']:
            record = self.leakage_guard.mark_record_compliance(record, training_patch)
        
        # Step 3: Ensure all mandatory fields present
        standardized = {
            # Entity identification
            'entity_id': record.get('entity_id', record.get('champion_name', 'unknown')),
            'entity_type': record.get('entity_type', self._infer_entity_type(record)),
            'patch_from': record.get('patch_from', record.get('patch_id', training_patch)),
            'patch_to': record.get('patch_to', record.get('patch_id', training_patch)),
            
            # Core metric value
            'metric_value': record.get('metric_value', record.get('value', record.get('winrate', 0.0))),
            
            # Evidence metadata (mandatory)
            'n': record.get('n', 0),
            'effective_n': record.get('effective_n', record.get('n', 0)),
            'uses_prior': record.get('uses_prior', False),
            'ci_lo': record.get('ci_lo', 0.0),
            'ci_hi': record.get('ci_hi', 1.0),
            'metric_version': record.get('metric_version', 'efp_v1.0'),
            'generated_at': record.get('generated_at', datetime.now().isoformat()),
            
            # Quality assurance (mandatory)
            'governance_tag': record.get('governance_tag', 'CONTEXT'),
            'data_quality_score': record.get('data_quality_score', 0.0),
            'leakage_guard': record.get('leakage_guard', '+1_patch_buffer'),
            
            # Preserve all original fields
            **record
        }
        
        # Add shock indicators if available and enabled
        if self.config.include_shock_indicators and 'shock_v2' not in standardized:
            standardized.update(self._add_shock_indicators(record))
        
        return standardized
    
    def _infer_entity_type(self, record: Dict[str, Any]) -> str:
        """Infer entity type from record content"""
        if 'champion_name' in record or 'champion_id' in record:
            return 'champion'
        elif 'item_id' in record or any('item' in str(k).lower() for k in record.keys()):
            return 'item'
        elif 'rune_id' in record or any('rune' in str(k).lower() for k in record.keys()):
            return 'rune'
        elif 'patch' in record or any('patch' in str(k).lower() for k in record.keys()):
            return 'patch'
        else:
            return 'meta'
    
    def _add_shock_indicators(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Add shock indicators to record if not present"""
        shock_fields = {}
        
        # Basic shock calculation if winrate change available
        if 'winrate_change' in record:
            shock_fields['shock_v2'] = abs(record['winrate_change']) * 10.0  # Scale to shock value
            shock_fields['shock_components'] = {
                'value': abs(record['winrate_change']) * 10.0,
                'scaling': 0.0,
                'cd': 0.0,
                'cost': 0.0,
                'gold_eff': 0.0,
                'onhit': 0.0,
                'tree_pos': 0.0
            }
        
        return shock_fields
    
    def prioritize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize records by governance tag and quality score
        CONFIDENT priority, CAUTION secondary, limit to 3K rows
        """
        # Sort by governance priority and quality score
        governance_order = {tag: i for i, tag in enumerate(self.config.governance_priority)}
        
        sorted_records = sorted(records, key=lambda r: (
            governance_order.get(r.get('governance_tag', 'CONTEXT'), 999),
            -r.get('data_quality_score', 0.0),  # Higher quality first
            -r.get('n', 0)  # Larger sample size first
        ))
        
        # Limit to max records
        limited_records = sorted_records[:self.config.max_records_per_file]
        
        logger.info(f"Prioritized {len(limited_records)} records from {len(records)} total")
        return limited_records
    
    def export_entity_panel(self, metrics: List[Dict[str, Any]], 
                          output_path: str, training_patch: str) -> None:
        """
        Export entity-level metrics (champion/item/rune level)
        """
        entity_records = []
        
        for metric in metrics:
            # Filter for entity-level metrics
            entity_type = metric.get('entity_type', self._infer_entity_type(metric))
            if entity_type in ['champion', 'item', 'rune']:
                standardized = self.standardize_metric_record(metric, entity_type, training_patch)
                
                # Validate compliance
                validation = self.validate_record_compliance(standardized)
                if validation['is_compliant']:
                    entity_records.append(standardized)
                else:
                    logger.warning(f"Record failed validation: {validation['missing_fields']}")
        
        # Prioritize and export
        prioritized_records = self.prioritize_records(entity_records)
        self._export_jsonl(prioritized_records, output_path, 'entity_panel')
        
        logger.info(f"Exported {len(prioritized_records)} entity panel records to {output_path}")
    
    def export_context_panel(self, metrics: List[Dict[str, Any]], 
                           output_path: str, training_patch: str) -> None:
        """
        Export context-level metrics (meta/patch level)
        """
        context_records = []
        
        for metric in metrics:
            # Filter for context-level metrics
            entity_type = metric.get('entity_type', self._infer_entity_type(metric))
            if entity_type in ['meta', 'patch']:
                standardized = self.standardize_metric_record(metric, entity_type, training_patch)
                
                # Validate compliance
                validation = self.validate_record_compliance(standardized)
                if validation['is_compliant']:
                    context_records.append(standardized)
        
        # Prioritize and export
        prioritized_records = self.prioritize_records(context_records)
        self._export_jsonl(prioritized_records, output_path, 'context_panel')
        
        logger.info(f"Exported {len(prioritized_records)} context panel records to {output_path}")
    
    def export_patch_summary(self, patch_comparisons: List[Dict[str, Any]], 
                           output_path: str) -> None:
        """
        Export patch-to-patch comparison summaries
        """
        patch_records = []
        
        for comparison in patch_comparisons:
            # Convert comparison to standardized record
            patch_record = {
                'entity_id': f"{comparison.get('patch_from', 'unknown')}_to_{comparison.get('patch_to', 'unknown')}",
                'entity_type': 'patch',
                'patch_from': comparison.get('patch_from', 'unknown'),
                'patch_to': comparison.get('patch_to', 'unknown'),
                'metric_value': comparison.get('meta_shift_score', 0.0),
                'n': comparison.get('champions_analyzed', 0),
                'effective_n': comparison.get('champions_analyzed', 0),
                'uses_prior': False,
                'ci_lo': 0.0,
                'ci_hi': 1.0,
                'metric_version': 'efp_v1.0',
                'generated_at': datetime.now().isoformat(),
                'governance_tag': 'CONFIDENT',
                'data_quality_score': 0.9,
                'leakage_guard': '+1_patch_buffer',
                
                # Additional patch-specific fields
                'meta_shift_score': comparison.get('meta_shift_score', 0.0),
                'top_winners': comparison.get('top_champions_gained', [])[:5],
                'top_losers': comparison.get('top_champions_lost', [])[:5],
                'statistical_significance': comparison.get('statistical_tests', {})
            }
            
            patch_records.append(patch_record)
        
        # Export without prioritization (usually small number of patch comparisons)
        self._export_jsonl(patch_records, output_path, 'patch_summary')
        
        logger.info(f"Exported {len(patch_records)} patch summary records to {output_path}")
    
    def _export_jsonl(self, records: List[Dict[str, Any]], 
                     output_path: str, export_type: str) -> None:
        """
        Export records as JSONL format
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Determine output file
        if self.config.compress_output:
            output_file = f"{output_path}.gz"
            file_open = gzip.open
        else:
            output_file = output_path
            file_open = open
        
        # Write JSONL
        with file_open(output_file, 'wt', encoding='utf-8') as f:
            for record in records:
                # Round numeric values for consistency
                rounded_record = self._round_numeric_values(record)
                f.write(json.dumps(rounded_record, ensure_ascii=False) + '\n')
        
        # Update export metadata
        self.export_metadata['files_generated'].append({
            'file_path': output_file,
            'export_type': export_type,
            'record_count': len(records),
            'compression': self.config.compress_output
        })
        self.export_metadata['total_records_processed'] += len(records)
    
    def _round_numeric_values(self, record: Dict[str, Any], decimals: int = 6) -> Dict[str, Any]:
        """Round numeric values for consistent output"""
        rounded = {}
        
        for key, value in record.items():
            if isinstance(value, float):
                rounded[key] = round(value, decimals)
            elif isinstance(value, dict):
                rounded[key] = self._round_numeric_values(value, decimals)
            elif isinstance(value, list):
                rounded[key] = [self._round_numeric_values(item, decimals) if isinstance(item, dict) 
                              else round(item, decimals) if isinstance(item, float) 
                              else item for item in value]
            else:
                rounded[key] = value
        
        return rounded
    
    def generate_quant_pack(self, data_sources: Dict[str, str], 
                          output_dir: str, training_patch: str = "14.23") -> Dict[str, Any]:
        """
        Generate complete Quant Pack v1.0 export
        
        Args:
            data_sources: Dictionary mapping data types to file paths
            output_dir: Output directory for JSONL files
            training_patch: Patch version for leakage prevention
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        all_metrics = []
        
        # Load all metric data sources
        for source_type, file_path in data_sources.items():
            if Path(file_path).exists():
                logger.info(f"Loading {source_type} from {file_path}")
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                records = data.get('records', data if isinstance(data, list) else [])
                
                # Tag records with source type
                for record in records:
                    record['source_type'] = source_type
                
                all_metrics.extend(records)
            else:
                logger.warning(f"Data source not found: {file_path}")
        
        logger.info(f"Loaded {len(all_metrics)} total metric records")
        
        # Export entity panel
        entity_output = output_path / "entity_panel.jsonl"
        self.export_entity_panel(all_metrics, str(entity_output), training_patch)
        
        # Export context panel  
        context_output = output_path / "context_panel.jsonl"
        self.export_context_panel(all_metrics, str(context_output), training_patch)
        
        # Load and export patch comparisons if available
        patch_output = output_path / "patch_summary.jsonl"
        patch_comparisons = []
        
        if 'patch_analysis' in data_sources:
            patch_file = data_sources['patch_analysis']
            if Path(patch_file).exists():
                with open(patch_file, 'r') as f:
                    patch_data = json.load(f)
                    patch_comparisons = [patch_data] if isinstance(patch_data, dict) else patch_data
        
        self.export_patch_summary(patch_comparisons, str(patch_output))
        
        # Generate export manifest
        manifest = {
            'quant_pack_version': 'v1.0',
            'schema_version': 'efp_v1.0',
            'generated_at': self.export_metadata['generated_at'],
            'training_patch': training_patch,
            'total_records': self.export_metadata['total_records_processed'],
            'files': self.export_metadata['files_generated'],
            'data_sources': data_sources,
            'export_config': {
                'max_records_per_file': self.config.max_records_per_file,
                'governance_priority': self.config.governance_priority,
                'compress_output': self.config.compress_output,
                'leakage_buffer_patches': self.config.leakage_buffer_patches
            },
            'agent_compatibility': {
                'format': 'jsonl',
                'encoding': 'utf-8',
                'compliance': 'efp_v1.0',
                'universal_agent_ready': True
            }
        }
        
        # Save manifest
        manifest_path = output_path / "quant_pack_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Generated Quant Pack v1.0 in {output_dir}")
        logger.info(f"Total records: {manifest['total_records']}")
        logger.info(f"Files: {len(manifest['files'])}")
        
        return manifest


def main():
    """Example usage of Quant Pack exporter"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export Quant Pack v1.0")
    parser.add_argument("--output_dir", required=True, help="Output directory for JSONL files")
    parser.add_argument("--training_patch", default="14.23", help="Training patch for leakage prevention")
    parser.add_argument("--max_records", type=int, default=3000, help="Max records per file")
    parser.add_argument("--compress", action="store_true", help="Compress output files")
    
    # Data source arguments
    parser.add_argument("--behavioral", help="Behavioral metrics JSON file")
    parser.add_argument("--quantitative", help="Quantitative metrics JSON file")
    parser.add_argument("--timeline", help="Timeline metrics JSON file")
    parser.add_argument("--patch_analysis", help="Patch analysis JSON file")
    
    args = parser.parse_args()
    
    # Configure export
    config = ExportConfig(
        max_records_per_file=args.max_records,
        compress_output=args.compress
    )
    
    # Initialize exporter
    exporter = QuantPackExporter(config=config)
    
    # Collect data sources
    data_sources = {}
    if args.behavioral:
        data_sources['behavioral'] = args.behavioral
    if args.quantitative:
        data_sources['quantitative'] = args.quantitative
    if args.timeline:
        data_sources['timeline'] = args.timeline
    if args.patch_analysis:
        data_sources['patch_analysis'] = args.patch_analysis
    
    if not data_sources:
        # Use default paths if no specific sources provided
        data_sources = {
            'behavioral': 'out/behavioral/behavioral_metrics.json',
            'quantitative': 'out/quantitative/quantitative_metrics_summary.json',
            'timeline': 'out/timeline/timeline_metrics.json',
            'patch_analysis': 'results/patch_analysis/patch_analysis_25.17_to_25.18.json'
        }
    
    # Generate Quant Pack
    manifest = exporter.generate_quant_pack(data_sources, args.output_dir, args.training_patch)
    
    # Print summary
    print(f"\n📦 Quant Pack v1.0 Generated")
    print(f"📊 Total Records: {manifest['total_records']}")
    print(f"📄 Files Generated: {len(manifest['files'])}")
    print(f"🛡️ Leakage Protection: +{config.leakage_buffer_patches} patch buffer")
    print(f"📁 Output Directory: {args.output_dir}")
    
    for file_info in manifest['files']:
        print(f"  - {file_info['export_type']}: {file_info['record_count']} records")
    
    print(f"\n✅ Universal agent-ready JSONL export complete")
    print(f"📋 Manifest: {args.output_dir}/quant_pack_manifest.json")


if __name__ == "__main__":
    main()