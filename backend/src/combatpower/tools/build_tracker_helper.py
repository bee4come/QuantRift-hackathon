"""
Helper tool to track and manage champion builds across patches

This tool helps you:
1. View current builds for any champion
2. Add patch-specific build changes
3. Generate reports on build evolution
4. Export/import build data

Usage:
    python tools/build_tracker_helper.py view Draven
    python tools/build_tracker_helper.py add Draven 14.24 --items 3142,6676,3814
    python tools/build_tracker_helper.py report Draven
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .services.meta_builds import meta_builds_db
from .services.patch_specific_builds import patch_specific_builds
from .services.patch_manager import patch_manager
from .services.data_provider import data_provider
import json


def view_champion_builds(champion_name: str):
    """View all builds for a champion across patches"""
    print(f"\n{'='*80}")
    print(f"BUILD HISTORY FOR {champion_name.upper()}")
    print(f"{'='*80}\n")
    
    # Get base build
    base_build = meta_builds_db.get_meta_build(champion_name)
    print(f"Base Build (Current Meta):")
    print(f"  Role: {base_build['role']}")
    print(f"  Items: {base_build['items']}")
    print(f"  Runes: {base_build['runes'][:4]}  # Primary")
    print(f"  Primary Style: {base_build['primary_style']}")
    print(f"  Sub Style: {base_build['sub_style']}")
    print(f"  Notes: {base_build.get('notes', 'N/A')}")
    
    # Check for patch-specific overrides
    build_changes = patch_specific_builds.get_build_changes_summary(champion_name)
    if build_changes:
        print(f"\n{'─'*80}")
        print(f"Patch-Specific Changes:")
        for patch, reason in sorted(build_changes.items()):
            build = patch_specific_builds.patch_overrides[champion_name][patch]
            print(f"\n  Patch {patch}:")
            print(f"    Items: {build['items']}")
            print(f"    Reason: {reason}")
    else:
        print(f"\n{'─'*80}")
        print(f"No patch-specific overrides found.")
        print(f"This champion uses the base build for all patches.")
    
    print(f"\n{'='*80}\n")


def add_patch_override(champion_name: str, patch: str, items: list, runes: list = None, 
                       primary_style: int = None, sub_style: int = None, reason: str = ""):
    """Add a new patch-specific build override"""
    
    # Get base build for defaults
    base_build = meta_builds_db.get_meta_build(champion_name)
    
    # Use base build values if not provided
    if runes is None:
        runes = base_build['runes']
    if primary_style is None:
        primary_style = base_build['primary_style']
    if sub_style is None:
        sub_style = base_build['sub_style']
    
    patch_specific_builds.add_patch_override(
        champion_name=champion_name,
        patch=patch,
        items=items,
        runes=runes,
        primary_style=primary_style,
        sub_style=sub_style,
        reason=reason
    )
    
    print(f"✅ Added build override for {champion_name} in patch {patch}")
    print(f"   Items: {items}")
    print(f"   Reason: {reason}")


def generate_report(champion_name: str = None):
    """Generate a build evolution report"""
    
    if champion_name:
        # Single champion report
        print(f"\n{'='*80}")
        print(f"BUILD EVOLUTION REPORT: {champion_name.upper()}")
        print(f"{'='*80}\n")
        
        all_patches = patch_manager.get_all_patches()
        base_build = meta_builds_db.get_meta_build(champion_name)
        
        print(f"{'Patch':<12} {'Items':<50} {'Notes':<20}")
        print('─'*80)
        
        for patch in all_patches:
            build = patch_specific_builds.get_build_for_patch(champion_name, patch, base_build)
            items_str = str(build['items'][:3]) + '...'  # Show first 3 items
            notes = build.get('notes', '')[:20]
            print(f"{patch:<12} {items_str:<50} {notes:<20}")
    
    else:
        # All champions with overrides
        print(f"\n{'='*80}")
        print(f"CHAMPIONS WITH PATCH-SPECIFIC BUILD OVERRIDES")
        print(f"{'='*80}\n")
        
        champions = patch_specific_builds.list_champions_with_overrides()
        
        if not champions:
            print("No patch-specific overrides found yet.")
            print("\nTo add overrides:")
            print("  python tools/build_tracker_helper.py add <champion> <patch> --items <item_ids>")
        else:
            for champ in sorted(champions):
                changes = patch_specific_builds.get_build_changes_summary(champ)
                print(f"{champ}:")
                for patch, reason in sorted(changes.items()):
                    print(f"  - Patch {patch}: {reason}")
        
        print(f"\n{'='*80}\n")


def export_builds_to_json(filename: str = "patch_builds.json"):
    """Export all patch-specific builds to JSON"""
    data = {
        'meta_builds': {},
        'patch_overrides': patch_specific_builds.patch_overrides,
        'meta_shifts': patch_specific_builds.meta_shift_patches
    }
    
    # Export some meta builds
    for champ in patch_specific_builds.list_champions_with_overrides():
        data['meta_builds'][champ] = meta_builds_db.get_meta_build(champ)
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Exported build data to {filename}")


def suggest_api_integration():
    """Suggest how to integrate with external APIs"""
    print(patch_specific_builds.export_for_api_integration())


def interactive_mode():
    """Interactive mode to add builds"""
    print("\n" + "="*80)
    print("INTERACTIVE BUILD TRACKER")
    print("="*80 + "\n")
    
    print("Let's add a patch-specific build override.\n")
    
    # Get champion
    champion = input("Champion name (e.g., Draven): ").strip()
    
    # Get patch
    all_patches = patch_manager.get_all_patches()
    print(f"\nAvailable patches: {', '.join(all_patches[:10])}...")
    patch = input("Patch version (e.g., 14.24): ").strip()
    
    # Get items
    print("\nEnter item IDs (comma-separated):")
    print("Examples: 3031=IE, 3072=BT, 3046=PD, 3142=Youmuu's, 6676=Collector")
    items_str = input("Items (e.g., 3031,3072,3046,3094,3508,3006): ").strip()
    items = [int(x.strip()) for x in items_str.split(',')]
    
    # Get reason
    reason = input("\nReason for build change: ").strip()
    
    # Confirm
    print(f"\n{'─'*80}")
    print(f"Champion: {champion}")
    print(f"Patch: {patch}")
    print(f"Items: {items}")
    print(f"Reason: {reason}")
    confirm = input("\nAdd this override? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        add_patch_override(champion, patch, items, reason=reason)
        print("\n✅ Override added successfully!")
    else:
        print("\n❌ Cancelled.")


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    if command == "view" and len(sys.argv) >= 3:
        champion = sys.argv[2]
        view_champion_builds(champion)
    
    elif command == "add" and len(sys.argv) >= 5:
        champion = sys.argv[2]
        patch = sys.argv[3]
        items_str = sys.argv[4].replace('--items=', '').replace('--items', '')
        items = [int(x.strip()) for x in items_str.split(',')]
        reason = ' '.join(sys.argv[5:]) if len(sys.argv) > 5 else ""
        add_patch_override(champion, patch, items, reason=reason)
    
    elif command == "report":
        champion = sys.argv[2] if len(sys.argv) >= 3 else None
        generate_report(champion)
    
    elif command == "export":
        filename = sys.argv[2] if len(sys.argv) >= 3 else "patch_builds.json"
        export_builds_to_json(filename)
    
    elif command == "api-guide":
        suggest_api_integration()
    
    elif command == "interactive":
        interactive_mode()
    
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

