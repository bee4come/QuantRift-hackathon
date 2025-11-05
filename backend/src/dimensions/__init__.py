"""
Dimension Tables Module
Provides static reference data for quantitative metrics calculations
"""

from .dim_stat_weights import DimStatWeights
from .dim_item_passive import DimItemPassive

__all__ = [
    'DimStatWeights',
    'DimItemPassive'
]