"""
Setup for tests - ensures imports work correctly
"""
import sys
import os

# Add parent directory to path so we can import services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

