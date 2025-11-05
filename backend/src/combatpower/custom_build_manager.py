"""
Custom Build Manager - Allows users to customize runes and items
Treats rune order and 6 item slots as variables that users can freely configure
"""
import json
import os
from typing import Dict, List, Any, Optional
from .services.patch_manager import patch_manager


class CustomBuildManager:
    """Manages user-defined rune and item configurations"""
    
    def __init__(self):
        self.builds_file = 'data/custom_builds.json'
        self.default_builds = self._get_default_builds()
        self.load_builds()
    
    def _get_default_builds(self) -> Dict[str, Any]:
        """Get default build configurations"""
        return {
            "champions": {
                "Draven": {
                    "items": [3031, 3094, 3046, 3085, 3006, 0],  # IE, BT, PD, Runaan's, Boots, Empty
                    "runes": {
                        "primary_style": 8000,  # Precision
                        "sub_style": 8200,      # Sorcery
                        "perk_ids": [8005, 9111, 9104, 8014, 8234, 8237, 5008, 5008, 5002]
                    }
                },
                "Jinx": {
                    "items": [3031, 3094, 3046, 3085, 3006, 0],  # IE, BT, PD, Runaan's, Boots, Empty
                    "runes": {
                        "primary_style": 8000,  # Precision
                        "sub_style": 8100,      # Domination
                        "perk_ids": [8008, 9111, 9104, 8014, 8139, 8135, 5005, 5008, 5002]
                    }
                },
                "Ahri": {
                    "items": [3089, 3135, 3020, 3003, 3006, 0],  # Rabadon's, Luden's, Frost Queen, Archangel's, Boots, Empty
                    "runes": {
                        "primary_style": 8200,  # Sorcery
                        "sub_style": 8300,      # Inspiration
                        "perk_ids": [8229, 8226, 8210, 8237, 8347, 8410, 5008, 5008, 5002]
                    }
                }
            },
            "global_settings": {
                "default_items": [0, 0, 0, 0, 0, 0],  # 6 empty item slots
                "default_runes": {
                    "primary_style": 8000,
                    "sub_style": 8200,
                    "perk_ids": [8005, 9111, 9104, 8014, 8234, 8237, 5008, 5008, 5002]
                }
            }
        }
    
    def load_builds(self):
        """Load custom build configurations"""
        try:
            if os.path.exists(self.builds_file):
                with open(self.builds_file, 'r', encoding='utf-8') as f:
                    self.builds = json.load(f)
            else:
                self.builds = self.default_builds.copy()
                self.save_builds()
        except Exception as e:
            print(f"Error loading builds: {e}")
            self.builds = self.default_builds.copy()
    
    def save_builds(self):
        """Save custom build configurations"""
        try:
            os.makedirs(os.path.dirname(self.builds_file), exist_ok=True)
            with open(self.builds_file, 'w', encoding='utf-8') as f:
                json.dump(self.builds, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving builds: {e}")
    
    def get_champion_build(self, champion_name: str, patch: str = None) -> Dict[str, Any]:
        """Get build configuration for specified champion"""
        if champion_name in self.builds["champions"]:
            return self.builds["champions"][champion_name]
        else:
            # Return default configuration
            return {
                "items": self.builds["global_settings"]["default_items"].copy(),
                "runes": self.builds["global_settings"]["default_runes"].copy()
            }
    
    def set_champion_build(self, champion_name: str, items: List[int], runes: Dict[str, Any]):
        """Set build configuration for specified champion"""
        if "champions" not in self.builds:
            self.builds["champions"] = {}
        
        self.builds["champions"][champion_name] = {
            "items": items[:6] if len(items) >= 6 else items + [0] * (6 - len(items)),
            "runes": runes
        }
        self.save_builds()
    
    def update_champion_items(self, champion_name: str, items: List[int]):
        """Update item configuration for specified champion"""
        if champion_name not in self.builds["champions"]:
            self.builds["champions"][champion_name] = {
                "items": [0, 0, 0, 0, 0, 0],
                "runes": self.builds["global_settings"]["default_runes"].copy()
            }
        
        self.builds["champions"][champion_name]["items"] = items[:6] if len(items) >= 6 else items + [0] * (6 - len(items))
        self.save_builds()
    
    def update_champion_runes(self, champion_name: str, runes: Dict[str, Any]):
        """Update rune configuration for specified champion"""
        if champion_name not in self.builds["champions"]:
            self.builds["champions"][champion_name] = {
                "items": self.builds["global_settings"]["default_items"].copy(),
                "runes": {}
            }
        
        self.builds["champions"][champion_name]["runes"] = runes
        self.save_builds()
    
    def get_all_champions(self) -> List[str]:
        """Get list of all configured champions"""
        return list(self.builds["champions"].keys())
    
    def delete_champion_build(self, champion_name: str):
        """Delete build configuration for specified champion"""
        if champion_name in self.builds["champions"]:
            del self.builds["champions"][champion_name]
            self.save_builds()
    
    def reset_to_default(self):
        """Reset to default configuration"""
        self.builds = self.default_builds.copy()
        self.save_builds()
    
    def export_builds(self, filename: str = None) -> str:
        """Export build configurations"""
        if filename is None:
            filename = f"custom_builds_export_{patch_manager.get_current_patch()}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.builds, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def import_builds(self, filename: str):
        """Import build configurations"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                imported_builds = json.load(f)
            
            # Validate imported data structure
            if "champions" in imported_builds and "global_settings" in imported_builds:
                self.builds = imported_builds
                self.save_builds()
                return True
            else:
                print("Invalid build file format")
                return False
        except Exception as e:
            print(f"Error importing builds: {e}")
            return False


# Global instance
custom_build_manager = CustomBuildManager()
