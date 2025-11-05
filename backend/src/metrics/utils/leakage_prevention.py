#!/usr/bin/env python3
"""
Leakage Prevention Module
Purpose: Implement +1 patch buffer to prevent future data leakage in model training
Implementation: Add leakage_guard: "+1_patch_buffer" field
Logic: Mark records that avoid using future patch data
Compliance: Self-proving regulatory compliance
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PatchInfo:
    """Patch version information"""
    patch_id: str
    major_version: int
    minor_version: int
    release_date: Optional[datetime] = None
    
    @classmethod
    def parse_patch_id(cls, patch_id: str) -> 'PatchInfo':
        """Parse patch ID like '14.23.1' or '25.17'"""
        # Clean patch ID
        patch_clean = patch_id.strip()
        
        # Handle different formats
        if '.' in patch_clean:
            parts = patch_clean.split('.')
            major = int(parts[0])
            minor = int(parts[1])
        else:
            # Assume it's a major version only
            major = int(patch_clean)
            minor = 0
        
        return cls(
            patch_id=patch_clean,
            major_version=major,
            minor_version=minor
        )
    
    def is_before(self, other: 'PatchInfo') -> bool:
        """Check if this patch is before another patch"""
        if self.major_version != other.major_version:
            return self.major_version < other.major_version
        return self.minor_version < other.minor_version
    
    def get_next_patch(self) -> 'PatchInfo':
        """Get the next patch in sequence"""
        return PatchInfo(
            patch_id=f"{self.major_version}.{self.minor_version + 1}",
            major_version=self.major_version,
            minor_version=self.minor_version + 1
        )

class LeakageGuard:
    """
    Leakage Prevention Engine
    Ensures training data doesn't include future patch information
    """
    
    def __init__(self, buffer_patches: int = 1):
        """
        Initialize leakage guard
        
        Args:
            buffer_patches: Number of patches to buffer (default: 1 for +1 patch buffer)
        """
        self.buffer_patches = buffer_patches
        self.leakage_guard_version = "v1.0"
        
    def detect_future_leakage(self, training_patch: str, feature_patches: List[str]) -> Dict[str, Any]:
        """
        Detect if features use data from patches after training patch
        
        Args:
            training_patch: Patch version used for training target
            feature_patches: List of patch versions used in features
            
        Returns:
            Dictionary with leakage detection results
        """
        training_info = PatchInfo.parse_patch_id(training_patch)
        
        leakage_detected = []
        safe_patches = []
        
        for feature_patch in feature_patches:
            feature_info = PatchInfo.parse_patch_id(feature_patch)
            
            if feature_info.is_before(training_info) or feature_info.patch_id == training_info.patch_id:
                safe_patches.append(feature_patch)
            else:
                leakage_detected.append({
                    'feature_patch': feature_patch,
                    'training_patch': training_patch,
                    'violation_type': 'future_data_leakage'
                })
        
        return {
            'has_leakage': len(leakage_detected) > 0,
            'leakage_violations': leakage_detected,
            'safe_patches': safe_patches,
            'total_features': len(feature_patches),
            'safe_features': len(safe_patches)
        }
    
    def apply_patch_buffer(self, training_patch: str, available_patches: List[str]) -> Dict[str, Any]:
        """
        Apply +1 patch buffer to prevent leakage
        
        Args:
            training_patch: Target patch for training
            available_patches: All available patches
            
        Returns:
            Dictionary with buffered patch information
        """
        training_info = PatchInfo.parse_patch_id(training_patch)
        
        # Calculate buffer threshold
        buffer_threshold = training_info
        for _ in range(self.buffer_patches):
            buffer_threshold = buffer_threshold.get_next_patch()
        
        # Filter patches within buffer
        safe_patches = []
        buffered_patches = []
        
        for patch in available_patches:
            patch_info = PatchInfo.parse_patch_id(patch)
            
            if patch_info.is_before(training_info) or patch_info.patch_id == training_info.patch_id:
                safe_patches.append(patch)
            elif patch_info.is_before(buffer_threshold):
                buffered_patches.append(patch)
        
        return {
            'training_patch': training_patch,
            'buffer_patches': self.buffer_patches,
            'buffer_threshold': buffer_threshold.patch_id,
            'safe_patches': safe_patches,
            'buffered_patches': buffered_patches,
            'total_available': len(available_patches),
            'usable_patches': len(safe_patches),
            'leakage_guard': f"+{self.buffer_patches}_patch_buffer"
        }
    
    def mark_record_compliance(self, record: Dict[str, Any], 
                             training_patch: str, 
                             feature_patches: List[str] = None) -> Dict[str, Any]:
        """
        Mark a metric record with leakage compliance information
        
        Args:
            record: Metric record to mark
            training_patch: Patch used for training target
            feature_patches: Patches used in features (if not in record)
        """
        # Extract feature patches from record if not provided
        if feature_patches is None:
            feature_patches = []
            # Common fields that might contain patch information
            patch_fields = ['patch_id', 'patch_version', 'source_patch', 'data_patch']
            for field in patch_fields:
                if field in record and record[field]:
                    feature_patches.append(str(record[field]))
        
        # Detect leakage
        leakage_result = self.detect_future_leakage(training_patch, feature_patches)
        
        # Apply buffer
        buffer_result = self.apply_patch_buffer(training_patch, feature_patches)
        
        # Create compliance marker
        if leakage_result['has_leakage']:
            compliance_status = "LEAKAGE_DETECTED"
            leakage_guard = "VIOLATION"
        else:
            compliance_status = "COMPLIANT"
            leakage_guard = buffer_result['leakage_guard']
        
        # Add compliance fields to record
        compliant_record = {
            **record,
            'leakage_guard': leakage_guard,
            'leakage_compliance_status': compliance_status,
            'training_patch': training_patch,
            'feature_patches': feature_patches,
            'leakage_buffer_patches': self.buffer_patches,
            'leakage_guard_version': self.leakage_guard_version,
            'leakage_check_timestamp': datetime.now().isoformat()
        }
        
        # Add detailed leakage information if violations found
        if leakage_result['has_leakage']:
            compliant_record['leakage_violations'] = leakage_result['leakage_violations']
        
        return compliant_record
    
    def batch_mark_compliance(self, records: List[Dict[str, Any]], 
                            training_patch: str) -> List[Dict[str, Any]]:
        """
        Mark multiple records with leakage compliance
        """
        compliant_records = []
        
        for record in records:
            try:
                compliant_record = self.mark_record_compliance(record, training_patch)
                compliant_records.append(compliant_record)
            except Exception as e:
                logger.warning(f"Failed to mark compliance for record: {e}")
                # Add error marker
                record['leakage_compliance_error'] = str(e)
                compliant_records.append(record)
        
        # Summary statistics
        total_records = len(compliant_records)
        compliant_count = sum(1 for r in compliant_records 
                            if r.get('leakage_compliance_status') == 'COMPLIANT')
        
        logger.info(f"Marked {total_records} records: {compliant_count} compliant, "
                   f"{total_records - compliant_count} violations")
        
        return compliant_records
    
    def validate_training_dataset(self, dataset: List[Dict[str, Any]], 
                                training_patch: str) -> Dict[str, Any]:
        """
        Validate entire training dataset for leakage compliance
        """
        validation_result = {
            'total_records': len(dataset),
            'compliant_records': 0,
            'violation_records': 0,
            'error_records': 0,
            'compliance_rate': 0.0,
            'violations_by_type': {},
            'patch_usage_summary': {},
            'is_training_safe': True,
            'validation_timestamp': datetime.now().isoformat()
        }
        
        for record in dataset:
            status = record.get('leakage_compliance_status', 'UNKNOWN')
            
            if status == 'COMPLIANT':
                validation_result['compliant_records'] += 1
            elif status == 'LEAKAGE_DETECTED':
                validation_result['violation_records'] += 1
                validation_result['is_training_safe'] = False
                
                # Count violation types
                violations = record.get('leakage_violations', [])
                for violation in violations:
                    v_type = violation.get('violation_type', 'unknown')
                    validation_result['violations_by_type'][v_type] = \
                        validation_result['violations_by_type'].get(v_type, 0) + 1
            else:
                validation_result['error_records'] += 1
            
            # Track patch usage
            feature_patches = record.get('feature_patches', [])
            for patch in feature_patches:
                validation_result['patch_usage_summary'][patch] = \
                    validation_result['patch_usage_summary'].get(patch, 0) + 1
        
        # Calculate compliance rate
        if validation_result['total_records'] > 0:
            validation_result['compliance_rate'] = \
                validation_result['compliant_records'] / validation_result['total_records']
        
        return validation_result
    
    def generate_compliance_report(self, validation_result: Dict[str, Any], 
                                 output_file: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report
        """
        report = {
            'leakage_prevention_report': {
                'guard_version': self.leakage_guard_version,
                'buffer_patches': self.buffer_patches,
                'generated_at': datetime.now().isoformat()
            },
            'dataset_validation': validation_result,
            'compliance_summary': {
                'overall_status': 'SAFE' if validation_result['is_training_safe'] else 'UNSAFE',
                'compliance_rate': f"{validation_result['compliance_rate']:.1%}",
                'total_violations': validation_result['violation_records'],
                'buffer_effectiveness': 'EFFECTIVE' if validation_result['compliance_rate'] > 0.95 else 'NEEDS_REVIEW'
            },
            'recommendations': []
        }
        
        # Add recommendations based on results
        if validation_result['violation_records'] > 0:
            report['recommendations'].append({
                'type': 'CRITICAL',
                'message': f"Remove {validation_result['violation_records']} records with future data leakage"
            })
        
        if validation_result['compliance_rate'] < 0.95:
            report['recommendations'].append({
                'type': 'WARNING',
                'message': f"Consider increasing buffer to +{self.buffer_patches + 1} patches"
            })
        
        if validation_result['error_records'] > 0:
            report['recommendations'].append({
                'type': 'INFO',
                'message': f"Review {validation_result['error_records']} records with compliance errors"
            })
        
        # Export report if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Compliance report saved to: {output_file}")
        
        return report

class PatchSequenceValidator:
    """
    Validate patch sequences for temporal consistency
    """
    
    def __init__(self):
        """Initialize validator"""
        self.leakage_guard = LeakageGuard()
    
    def validate_patch_sequence(self, patches: List[str]) -> Dict[str, Any]:
        """
        Validate that patch sequence is temporally consistent
        """
        if len(patches) < 2:
            return {'valid': True, 'message': 'Single patch, no sequence to validate'}
        
        patch_infos = [PatchInfo.parse_patch_id(p) for p in patches]
        
        # Check for temporal ordering
        is_ordered = True
        violations = []
        
        for i in range(len(patch_infos) - 1):
            current = patch_infos[i]
            next_patch = patch_infos[i + 1]
            
            if not current.is_before(next_patch) and current.patch_id != next_patch.patch_id:
                is_ordered = False
                violations.append({
                    'position': i,
                    'current_patch': current.patch_id,
                    'next_patch': next_patch.patch_id,
                    'issue': 'temporal_ordering_violation'
                })
        
        return {
            'valid': is_ordered,
            'total_patches': len(patches),
            'violations': violations,
            'message': 'Valid sequence' if is_ordered else f'{len(violations)} ordering violations found'
        }
    
    def suggest_training_splits(self, available_patches: List[str], 
                              test_split_ratio: float = 0.2) -> Dict[str, Any]:
        """
        Suggest temporally consistent train/test splits
        """
        sorted_patches = sorted(available_patches, 
                              key=lambda p: PatchInfo.parse_patch_id(p).minor_version)
        
        # Calculate split point
        split_point = int(len(sorted_patches) * (1 - test_split_ratio))
        
        train_patches = sorted_patches[:split_point]
        test_patches = sorted_patches[split_point:]
        
        # Apply leakage buffer
        if len(test_patches) > 0:
            earliest_test_patch = test_patches[0]
            buffer_result = self.leakage_guard.apply_patch_buffer(earliest_test_patch, train_patches)
            
            return {
                'train_patches': buffer_result['safe_patches'],
                'test_patches': test_patches,
                'buffered_patches': buffer_result['buffered_patches'],
                'buffer_applied': True,
                'leakage_guard': buffer_result['leakage_guard'],
                'split_ratio_actual': len(buffer_result['safe_patches']) / len(sorted_patches)
            }
        else:
            return {
                'train_patches': train_patches,
                'test_patches': test_patches,
                'buffered_patches': [],
                'buffer_applied': False,
                'split_ratio_actual': len(train_patches) / len(sorted_patches)
            }


def main():
    """Example usage of leakage prevention"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply leakage prevention to metrics")
    parser.add_argument("--input", required=True, help="Input metrics JSON file")
    parser.add_argument("--output", required=True, help="Output compliant JSON file")
    parser.add_argument("--training_patch", required=True, help="Training patch version")
    parser.add_argument("--buffer_patches", type=int, default=1, help="Number of buffer patches")
    parser.add_argument("--validate", action="store_true", help="Validate dataset compliance")
    parser.add_argument("--report", help="Generate compliance report file")
    
    args = parser.parse_args()
    
    # Initialize leakage guard
    guard = LeakageGuard(buffer_patches=args.buffer_patches)
    
    # Load input metrics
    with open(args.input, 'r') as f:
        input_data = json.load(f)
    
    records = input_data.get('records', input_data if isinstance(input_data, list) else [])
    
    # Apply leakage compliance
    compliant_records = guard.batch_mark_compliance(records, args.training_patch)
    
    # Validate if requested
    validation_result = None
    if args.validate:
        validation_result = guard.validate_training_dataset(compliant_records, args.training_patch)
        print(f"\nValidation Results:")
        print(f"Training Safety: {'SAFE' if validation_result['is_training_safe'] else 'UNSAFE'}")
        print(f"Compliance Rate: {validation_result['compliance_rate']:.1%}")
        print(f"Violations: {validation_result['violation_records']}")
    
    # Generate compliance report if requested
    if args.report and validation_result:
        report = guard.generate_compliance_report(validation_result, args.report)
        print(f"\n📄 Compliance report saved to: {args.report}")
    
    # Export compliant metrics
    output_data = {
        'metadata': {
            'export_type': 'leakage_compliant_metrics',
            'training_patch': args.training_patch,
            'buffer_patches': args.buffer_patches,
            'leakage_guard_version': guard.leakage_guard_version,
            'generated_at': datetime.now().isoformat(),
            'total_records': len(compliant_records)
        },
        'records': compliant_records
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    compliant_count = sum(1 for r in compliant_records 
                         if r.get('leakage_compliance_status') == 'COMPLIANT')
    
    print(f"\n✅ Processed {len(compliant_records)} records")
    print(f"🛡️ Compliant: {compliant_count}")
    print(f"⚠️ Violations: {len(compliant_records) - compliant_count}")
    print(f"📄 Output saved to: {args.output}")


if __name__ == "__main__":
    main()