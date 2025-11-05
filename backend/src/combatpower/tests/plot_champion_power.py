"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

Plot champion combat power across patches
"""
import matplotlib.pyplot as plt
from datetime import datetime
from .services.patch_manager import patch_manager
from .services.multi_patch_data import multi_patch_data
from .services.combat_power import combat_power_calculator


def get_champion_power_timeline(champion_name: str, patches: list = None):
    """Get champion power data for multiple patches"""
    if patches is None:
        # Use all available patches
        patches = patch_manager.get_all_patches()
    
    timeline = []
    
    for patch in patches:
        try:
            # Get champion data
            champions = multi_patch_data.get_champions_for_patch(patch)
            
            if champion_name not in champions:
                continue
            
            champion_detail = multi_patch_data.get_champion_detail_for_patch(patch, champion_name)
            champion_stats = champions[champion_name]['stats']
            
            # Calculate power
            base_power = combat_power_calculator.calculate_base_stats_power(champion_stats, 18)
            skill_power = combat_power_calculator.calculate_skill_power(champion_detail)
            total_power = base_power + skill_power
            
            # Get patch date
            patch_date = patch_manager.get_patch_date(patch)
            
            timeline.append({
                'patch': patch,
                'date': patch_date,
                'total_power': total_power,
                'base_power': base_power,
                'skill_power': skill_power,
                'base_ad': champion_stats.get('attackdamage', 0),
                'base_hp': champion_stats.get('hp', 0)
            })
            
        except Exception as e:
            print(f"Error fetching {patch}: {e}")
            continue
    
    return timeline


def plot_champion_power(champion_name: str, patches: list = None, show_components: bool = True):
    """
    Create a plot of champion combat power across patches
    
    Args:
        champion_name: Champion name (e.g., 'Draven', 'KSante')
        patches: List of patches to include (None = all patches)
        show_components: Whether to show base/skill power breakdown
    """
    print(f"Fetching data for {champion_name}...")
    timeline = get_champion_power_timeline(champion_name, patches)
    
    if not timeline:
        print(f"No data found for {champion_name}")
        return
    
    # Extract data for plotting
    patch_labels = [item['patch'] for item in timeline]
    dates = [item['date'] for item in timeline]
    total_powers = [item['total_power'] for item in timeline]
    base_powers = [item['base_power'] for item in timeline]
    skill_powers = [item['skill_power'] for item in timeline]
    
    # Create figure
    if show_components:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(14, 6))
    
    # Plot 1: Total Combat Power
    ax1.plot(patch_labels, total_powers, marker='o', linewidth=2, markersize=8, color='#0066cc')
    ax1.set_xlabel('Patch Version', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Total Combat Power', fontsize=12, fontweight='bold')
    ax1.set_title(f'{champion_name} - Combat Power Across Patches', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Add value labels on points
    for i, (patch, power) in enumerate(zip(patch_labels, total_powers)):
        ax1.annotate(f'{power:.1f}', 
                    (patch, power),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha='center',
                    fontsize=8)
    
    # Highlight changes
    for i in range(1, len(total_powers)):
        diff = total_powers[i] - total_powers[i-1]
        if abs(diff) > 1:  # Significant change
            color = 'green' if diff > 0 else 'red'
            ax1.axvspan(i-0.5, i+0.5, alpha=0.1, color=color)
            
            # Add change annotation
            percent = (diff / total_powers[i-1] * 100) if total_powers[i-1] > 0 else 0
            ax1.text(i, total_powers[i], 
                    f'{diff:+.1f}\n({percent:+.1f}%)',
                    ha='center', va='bottom',
                    fontsize=7, color=color, fontweight='bold')
    
    # Plot 2: Component Breakdown (if requested)
    if show_components:
        ax2.plot(patch_labels, base_powers, marker='s', linewidth=2, markersize=6, 
                label='Base Stats Power', color='#ff6600')
        ax2.plot(patch_labels, skill_powers, marker='^', linewidth=2, markersize=6,
                label='Skill Power', color='#9933ff')
        ax2.set_xlabel('Patch Version', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Combat Power', fontsize=12, fontweight='bold')
        ax2.set_title('Power Components Breakdown', fontsize=12, fontweight='bold')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Save plot
    filename = f'{champion_name.lower()}_combat_power.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved as: {filename}")
    
    # Show plot
    plt.show()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary for {champion_name}")
    print(f"{'='*60}")
    print(f"Patches analyzed: {len(timeline)}")
    print(f"Date range: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
    print(f"\nPower range: {min(total_powers):.2f} - {max(total_powers):.2f}")
    print(f"Average power: {sum(total_powers)/len(total_powers):.2f}")
    
    # Find biggest changes
    changes = []
    for i in range(1, len(timeline)):
        diff = total_powers[i] - total_powers[i-1]
        if abs(diff) > 0.1:
            percent = (diff / total_powers[i-1] * 100) if total_powers[i-1] > 0 else 0
            changes.append((patch_labels[i-1], patch_labels[i], diff, percent))
    
    if changes:
        print(f"\nSignificant changes:")
        for prev_patch, curr_patch, diff, percent in sorted(changes, key=lambda x: abs(x[2]), reverse=True):
            status = "BUFF" if diff > 0 else "NERF"
            print(f"  {prev_patch} -> {curr_patch}: {diff:+.2f} ({percent:+.2f}%) - {status}")
    else:
        print(f"\nNo significant changes detected across patches")


def plot_multiple_champions(champions: list, patches: list = None):
    """
    Compare multiple champions on the same plot
    
    Args:
        champions: List of champion names
        patches: List of patches to include
    """
    fig, ax = plt.subplots(figsize=(16, 8))
    
    colors = ['#0066cc', '#ff6600', '#9933ff', '#00cc66', '#cc0066', '#ffcc00']
    
    for i, champion_name in enumerate(champions):
        print(f"Fetching data for {champion_name}...")
        timeline = get_champion_power_timeline(champion_name, patches)
        
        if not timeline:
            print(f"No data found for {champion_name}")
            continue
        
        patch_labels = [item['patch'] for item in timeline]
        total_powers = [item['total_power'] for item in timeline]
        
        color = colors[i % len(colors)]
        ax.plot(patch_labels, total_powers, marker='o', linewidth=2, markersize=6,
               label=champion_name, color=color)
    
    ax.set_xlabel('Patch Version', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Combat Power', fontsize=12, fontweight='bold')
    ax.set_title('Champion Combat Power Comparison', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    filename = 'champions_comparison.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\nComparison plot saved as: {filename}")
    
    plt.show()


if __name__ == '__main__':
    import sys
    
    # Check if champion name provided as argument
    if len(sys.argv) > 1:
        champion_name = sys.argv[1]
        print(f"\nGenerating plot for {champion_name}...")
        plot_champion_power(champion_name)
    else:
        # Demo: Plot multiple champions
        print("\n" + "="*60)
        print("DEMO: Individual Champion Plots")
        print("="*60)
        
        # K'Sante (has buffs)
        print("\n1. K'Sante (showing recent patches with buff)")
        plot_champion_power('KSante', patches=['14.19', '14.20', '14.21', '14.22', '14.23', '14.24'])
        
        # Draven (stable)
        print("\n2. Draven (stable across patches)")
        plot_champion_power('Draven', patches=['14.19', '14.20', '14.21', '14.22', '14.23'])
        
        print("\n" + "="*60)
        print("DEMO: Multi-Champion Comparison")
        print("="*60)
        
        # Compare multiple champions
        print("\n3. Comparing multiple champions")
        plot_multiple_champions(
            ['Draven', 'Jinx', 'Vayne', 'KSante', 'Zed'],
            patches=['14.19', '14.20', '14.21', '14.22', '14.23']
        )
        
        print("\n" + "="*60)
        print("Done! Check the generated PNG files.")
        print("="*60)
        print("\nUsage: python plot_champion_power.py <ChampionName>")
        print("Example: python plot_champion_power.py Ahri")

