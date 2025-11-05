#!/usr/bin/env python3
"""
Daily OP.GG Win Rate Refresh Script
Run this daily to update champion win rates and primary lanes

Usage:
    python3 refresh_opgg_winrates.py

Cron example (daily at 3 AM):
    0 3 * * * cd /path/to/combatpower && python3 refresh_opgg_winrates.py
"""
from .services.opgg_winrate_fetcher import opgg_winrate_fetcher


def main():
    print("\n" + "=" * 70)
    print("OP.GG Win Rate Daily Refresh")
    print("=" * 70 + "\n")
    
    # Refresh the cache
    opgg_winrate_fetcher.refresh_cache()
    
    print("\nRefresh complete! Primary lanes have been updated.\n")


if __name__ == '__main__':
    main()

