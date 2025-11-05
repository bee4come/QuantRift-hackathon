#!/usr/bin/env python3
"""
Evidence Metadata Standard Module
Purpose: Proof of Quality for all quantitative metrics
Required Fields: n, effective_n, uses_prior, ci_lo, ci_hi, metric_version, generated_at
Compliance: Preserve these in all JSONL exports
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import json
from scipy import stats
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EvidenceMetadata:
    """
    Standard evidence metadata for all quantitative metrics
    Mandatory fields for statistical quality assurance
    """
    # Core sample size evidence
    n: int                           # Original sample size
    effective_n: int                 # Statistical effective sample size
    uses_prior: bool                 # Whether Beta-Binomial prior was used
    
    # Statistical confidence intervals
    ci_lo: float                     # Wilson confidence interval lower bound
    ci_hi: float                     # Wilson confidence interval upper bound
    
    # Framework versioning and traceability
    metric_version: str              # Framework version (e.g., "efp_v1.0")
    generated_at: str                # ISO timestamp of generation
    
    # Additional quality indicators with defaults
    ci_level: float = 0.95          # Confidence level (default 95%)
    governance_tag: str = "CONTEXT"  # CONFIDENT/CAUTION/CONTEXT
    data_quality_score: float = 0.0 # 0-1 quality score
    leakage_guard: str = ""          # Leakage prevention marker
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvidenceMetadata':
        """Create from dictionary"""
        return cls(**data)

class EvidenceStandardizer:
    """
    Evidence Metadata Standardization Engine
    Ensures all metrics include mandatory statistical fields
    """
    
    def __init__(self, framework_version: str = "efp_v1.0"):
        """Initialize with framework version"""
        self.framework_version = framework_version
        self.current_timestamp = datetime.now().isoformat()
        
    def wilson_confidence_interval(self, successes: int, trials: int, 
                                 alpha: float = 0.05) -> Tuple[float, float, float]:
        """
        Calculate Wilson confidence interval for binomial proportion
        Returns: (proportion, ci_lower, ci_upper)
        """
        if trials == 0:
            return 0.0, 0.0, 0.0
            
        z = stats.norm.ppf(1 - alpha/2)  # 1.96 for 95% CI
        p = successes / trials
        
        center = (p + z**2 / (2 * trials)) / (1 + z**2 / trials)
        margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / (1 + z**2 / trials)
        
        ci_lower = max(0, center - margin)
        ci_upper = min(1, center + margin)
        
        return p, ci_lower, ci_upper
    
    def calculate_effective_sample_size(self, n_original: int, uses_prior: bool = False, 
                                      prior_weight: float = 50.0) -> int:
        """
        Calculate effective sample size considering prior information
        """
        if not uses_prior:
            return n_original
            
        # Beta-Binomial effective sample size with prior
        # Prior acts as additional pseudo-observations
        effective_n = n_original + prior_weight
        
        return int(effective_n)
    
    def determine_governance_tag(self, n: int, effective_n: int, 
                               ci_width: float) -> str:
        """
        Determine governance tag based on evidence quality
        """
        if effective_n >= 100 and ci_width < 0.1:
            return "CONFIDENT"
        elif effective_n >= 50 and ci_width < 0.15:
            return "CAUTION"
        else:
            return "CONTEXT"
    
    def calculate_data_quality_score(self, n: int, effective_n: int, 
                                   ci_width: float, has_outliers: bool = False) -> float:
        """
        Calculate 0-1 data quality score
        """
        # Base score from sample size
        sample_score = min(1.0, effective_n / 100.0)
        
        # Confidence score (narrower CI = higher quality)
        confidence_score = max(0.0, 1.0 - ci_width * 5.0)  # 0.2 CI width = 0 score
        
        # Outlier penalty
        outlier_penalty = 0.1 if has_outliers else 0.0
        
        # Combined score
        quality_score = (sample_score * 0.6 + confidence_score * 0.4) - outlier_penalty
        
        return max(0.0, min(1.0, quality_score))
    
    def create_evidence_metadata(self, n: int, successes: int = None, 
                               uses_prior: bool = False, prior_weight: float = 50.0,
                               has_outliers: bool = False, 
                               leakage_guard: str = "") -> EvidenceMetadata:
        """
        Create complete evidence metadata for a metric
        
        Args:
            n: Original sample size
            successes: Number of successes (for Wilson CI calculation)
            uses_prior: Whether Beta-Binomial prior was used
            prior_weight: Weight of prior information
            has_outliers: Whether data has outliers
            leakage_guard: Leakage prevention marker
        """
        # Calculate effective sample size
        effective_n = self.calculate_effective_sample_size(n, uses_prior, prior_weight)
        
        # Calculate Wilson confidence interval if successes provided
        if successes is not None:
            proportion, ci_lo, ci_hi = self.wilson_confidence_interval(successes, n)
        else:
            # For non-binomial metrics, use approximate CI based on sample size
            ci_lo = 0.0
            ci_hi = 1.0
            if n > 0:
                # Approximate CI width based on sample size
                ci_width = 1.96 / np.sqrt(n)
                ci_lo = 0.5 - ci_width/2
                ci_hi = 0.5 + ci_width/2
        
        ci_width = ci_hi - ci_lo
        
        # Determine governance tag
        governance_tag = self.determine_governance_tag(n, effective_n, ci_width)
        
        # Calculate quality score
        data_quality_score = self.calculate_data_quality_score(
            n, effective_n, ci_width, has_outliers
        )
        
        return EvidenceMetadata(
            n=n,
            effective_n=effective_n,
            uses_prior=uses_prior,
            ci_lo=ci_lo,
            ci_hi=ci_hi,
            metric_version=self.framework_version,
            generated_at=self.current_timestamp,
            governance_tag=governance_tag,
            data_quality_score=data_quality_score,
            leakage_guard=leakage_guard
        )
    
    def standardize_metric_record(self, metric_data: Dict[str, Any], 
                                metric_type: str = "unknown") -> Dict[str, Any]:
        """
        Add evidence metadata to existing metric record
        """
        # Extract sample size information
        n = metric_data.get('sample_size', metric_data.get('n_games', 0))
        successes = metric_data.get('n_wins', metric_data.get('successes', None))
        
        # Check for prior usage indicators
        uses_prior = any(key in metric_data for key in ['prior_alpha', 'prior_beta', 'shrinkage'])
        
        # Check for outliers
        has_outliers = metric_data.get('has_outliers', False)
        
        # Leakage guard (will be enhanced in next requirement)
        leakage_guard = metric_data.get('leakage_guard', '')
        
        # Create evidence metadata
        evidence = self.create_evidence_metadata(
            n=n,
            successes=successes,
            uses_prior=uses_prior,
            has_outliers=has_outliers,
            leakage_guard=leakage_guard
        )
        
        # Create standardized record
        standardized_record = {
            # Original metric data
            **metric_data,
            
            # Mandatory evidence fields
            'n': evidence.n,
            'effective_n': evidence.effective_n,
            'uses_prior': evidence.uses_prior,
            'ci_lo': evidence.ci_lo,
            'ci_hi': evidence.ci_hi,
            'metric_version': evidence.metric_version,
            'generated_at': evidence.generated_at,
            
            # Quality indicators
            'governance_tag': evidence.governance_tag,
            'data_quality_score': evidence.data_quality_score,
            'leakage_guard': evidence.leakage_guard,
            
            # Additional metadata
            'metric_type': metric_type,
            'evidence_metadata_version': '1.0'
        }
        
        return standardized_record
    
    def batch_standardize_metrics(self, metrics: List[Dict[str, Any]], 
                                metric_type: str = "unknown") -> List[Dict[str, Any]]:
        """
        Standardize multiple metric records
        """
        standardized_metrics = []
        
        for metric in metrics:
            try:
                standardized = self.standardize_metric_record(metric, metric_type)
                standardized_metrics.append(standardized)
            except Exception as e:
                logger.warning(f"Failed to standardize metric: {e}")
                # Include original metric with error flag
                metric['standardization_error'] = str(e)
                standardized_metrics.append(metric)
        
        logger.info(f"Standardized {len(standardized_metrics)} metrics of type: {metric_type}")
        return standardized_metrics
    
    def validate_evidence_compliance(self, metric_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that metric record contains all mandatory evidence fields
        """
        mandatory_fields = [
            'n', 'effective_n', 'uses_prior', 'ci_lo', 'ci_hi', 
            'metric_version', 'generated_at'
        ]
        
        validation_result = {
            'is_compliant': True,
            'missing_fields': [],
            'field_types_valid': True,
            'validation_errors': []
        }
        
        # Check for missing fields
        for field in mandatory_fields:
            if field not in metric_record:
                validation_result['missing_fields'].append(field)
                validation_result['is_compliant'] = False
        
        # Check field types
        type_checks = {
            'n': int,
            'effective_n': int,
            'uses_prior': bool,
            'ci_lo': (int, float),
            'ci_hi': (int, float),
            'metric_version': str,
            'generated_at': str
        }
        
        for field, expected_type in type_checks.items():
            if field in metric_record:
                if not isinstance(metric_record[field], expected_type):
                    validation_result['validation_errors'].append(
                        f"Field '{field}' has type {type(metric_record[field])}, expected {expected_type}"
                    )
                    validation_result['field_types_valid'] = False
                    validation_result['is_compliant'] = False
        
        # Check logical constraints
        if 'n' in metric_record and 'effective_n' in metric_record:
            if metric_record['effective_n'] < metric_record['n']:
                validation_result['validation_errors'].append(
                    "effective_n cannot be less than n (without prior information)"
                )
                validation_result['is_compliant'] = False
        
        if 'ci_lo' in metric_record and 'ci_hi' in metric_record:
            if metric_record['ci_lo'] >= metric_record['ci_hi']:
                validation_result['validation_errors'].append(
                    "ci_lo must be less than ci_hi"
                )
                validation_result['is_compliant'] = False
        
        return validation_result
    
    def batch_validate_compliance(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate evidence compliance for multiple metrics
        """
        total_metrics = len(metrics)
        compliant_count = 0
        validation_summary = {
            'total_metrics': total_metrics,
            'compliant_metrics': 0,
            'compliance_rate': 0.0,
            'common_missing_fields': {},
            'common_errors': {},
            'detailed_results': []
        }
        
        for i, metric in enumerate(metrics):
            validation = self.validate_evidence_compliance(metric)
            validation_summary['detailed_results'].append({
                'metric_index': i,
                'is_compliant': validation['is_compliant'],
                'missing_fields': validation['missing_fields'],
                'validation_errors': validation['validation_errors']
            })
            
            if validation['is_compliant']:
                compliant_count += 1
            
            # Track common issues
            for field in validation['missing_fields']:
                validation_summary['common_missing_fields'][field] = \
                    validation_summary['common_missing_fields'].get(field, 0) + 1
            
            for error in validation['validation_errors']:
                validation_summary['common_errors'][error] = \
                    validation_summary['common_errors'].get(error, 0) + 1
        
        validation_summary['compliant_metrics'] = compliant_count
        validation_summary['compliance_rate'] = compliant_count / total_metrics if total_metrics > 0 else 0.0
        
        return validation_summary

class LegacyMetricMigrator:
    """
    Migrate existing metrics to evidence metadata standard
    """
    
    def __init__(self, framework_version: str = "efp_v1.0"):
        """Initialize migrator"""
        self.standardizer = EvidenceStandardizer(framework_version)
    
    def migrate_behavioral_metrics(self, behavioral_file: str) -> List[Dict[str, Any]]:
        """Migrate behavioral metrics to evidence standard"""
        with open(behavioral_file, 'r') as f:
            data = json.load(f)
        
        metrics = data.get('records', [])
        migrated = self.standardizer.batch_standardize_metrics(metrics, 'behavioral')
        
        return migrated
    
    def migrate_quantitative_metrics(self, quantitative_file: str) -> List[Dict[str, Any]]:
        """Migrate quantitative metrics to evidence standard"""
        with open(quantitative_file, 'r') as f:
            data = json.load(f)
        
        metrics = data.get('records', [])
        migrated = self.standardizer.batch_standardize_metrics(metrics, 'quantitative')
        
        return migrated
    
    def migrate_timeline_metrics(self, timeline_file: str) -> List[Dict[str, Any]]:
        """Migrate timeline metrics to evidence standard"""
        with open(timeline_file, 'r') as f:
            data = json.load(f)
        
        metrics = data.get('records', [])
        migrated = self.standardizer.batch_standardize_metrics(metrics, 'timeline')
        
        return migrated


def main():
    """Example usage of evidence metadata standardization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Standardize metrics with evidence metadata")
    parser.add_argument("--input", required=True, help="Input metrics JSON file")
    parser.add_argument("--output", required=True, help="Output standardized JSON file")
    parser.add_argument("--metric_type", default="unknown", help="Type of metrics")
    parser.add_argument("--validate", action="store_true", help="Validate compliance")
    
    args = parser.parse_args()
    
    # Initialize standardizer
    standardizer = EvidenceStandardizer()
    
    # Load input metrics
    with open(args.input, 'r') as f:
        input_data = json.load(f)
    
    metrics = input_data.get('records', input_data if isinstance(input_data, list) else [])
    
    # Standardize metrics
    standardized = standardizer.batch_standardize_metrics(metrics, args.metric_type)
    
    # Validate if requested
    if args.validate:
        validation = standardizer.batch_validate_compliance(standardized)
        print(f"\nValidation Results:")
        print(f"Compliance Rate: {validation['compliance_rate']:.1%}")
        print(f"Compliant Metrics: {validation['compliant_metrics']}/{validation['total_metrics']}")
        
        if validation['common_missing_fields']:
            print(f"\nCommon Missing Fields:")
            for field, count in validation['common_missing_fields'].items():
                print(f"  {field}: {count} metrics")
    
    # Export standardized metrics
    output_data = {
        'metadata': {
            'export_type': 'evidence_standardized_metrics',
            'metric_type': args.metric_type,
            'framework_version': standardizer.framework_version,
            'generated_at': standardizer.current_timestamp,
            'total_records': len(standardized),
            'evidence_fields': ['n', 'effective_n', 'uses_prior', 'ci_lo', 'ci_hi', 'metric_version', 'generated_at']
        },
        'records': standardized
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Standardized {len(standardized)} metrics")
    print(f"📄 Output saved to: {args.output}")


if __name__ == "__main__":
    main()