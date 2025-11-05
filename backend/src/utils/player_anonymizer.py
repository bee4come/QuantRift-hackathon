#!/usr/bin/env python3
"""
Player Anonymization System
安全的玩家身份匿名化和哈希映射系统
"""

import hashlib
import json
import secrets
from pathlib import Path
from typing import Dict, Optional, Set
import base64

class PlayerAnonymizer:
    """玩家匿名化映射器"""

    def __init__(self,
                 salt_file: str = "data/anonymization_salt.json",
                 mapping_file: str = "data/player_mappings.json"):
        self.salt_file = Path(salt_file)
        self.mapping_file = Path(mapping_file)

        # 加载或生成salt
        self.salt = self._load_or_generate_salt()

        # 加载现有映射
        self.puuid_to_hash = {}
        self.hash_to_puuid = {}
        self._load_existing_mappings()

    def _load_or_generate_salt(self) -> bytes:
        """加载或生成新的salt"""
        if self.salt_file.exists():
            try:
                with open(self.salt_file, 'r') as f:
                    data = json.load(f)
                    return base64.b64decode(data['salt'].encode())
            except Exception as e:
                print(f"⚠️ 加载salt失败: {e}, 生成新salt")

        # 生成新的随机salt
        salt = secrets.token_bytes(32)  # 256位随机salt

        # 保存salt (base64编码)
        salt_data = {
            'salt': base64.b64encode(salt).decode(),
            'algorithm': 'SHA-256',
            'created_at': '2024-09-28T00:00:00Z',
            'warning': 'DO NOT SHARE OR LOSE THIS FILE - 丢失此文件将无法恢复匿名化映射'
        }

        self.salt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.salt_file, 'w') as f:
            json.dump(salt_data, f, indent=2)

        print(f"🔐 生成新的匿名化salt: {self.salt_file}")
        return salt

    def _load_existing_mappings(self):
        """加载现有的映射关系"""
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r') as f:
                    data = json.load(f)
                    self.puuid_to_hash = data.get('puuid_to_hash', {})
                    self.hash_to_puuid = data.get('hash_to_puuid', {})
                print(f"📋 加载了 {len(self.puuid_to_hash)} 个现有映射")
            except Exception as e:
                print(f"⚠️ 加载映射失败: {e}, 使用空映射")

    def _save_mappings(self):
        """保存映射关系到文件"""
        mapping_data = {
            'puuid_to_hash': self.puuid_to_hash,
            'hash_to_puuid': self.hash_to_puuid,
            'metadata': {
                'total_mappings': len(self.puuid_to_hash),
                'algorithm': 'SHA-256',
                'last_updated': '2024-09-28T00:00:00Z'
            }
        }

        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mapping_file, 'w') as f:
            json.dump(mapping_data, f, indent=2)

    def _hash_puuid(self, puuid: str) -> str:
        """
        使用SHA-256和salt对PUUID进行哈希

        Args:
            puuid: 原始PUUID

        Returns:
            哈希后的16进制字符串
        """
        # 使用salt + puuid进行哈希
        hasher = hashlib.sha256()
        hasher.update(self.salt)
        hasher.update(puuid.encode('utf-8'))

        # 返回前16位字符 (64位)，足够唯一且紧凑
        return hasher.hexdigest()[:16]

    def anonymize_puuid(self, puuid: str) -> str:
        """
        匿名化单个PUUID

        Args:
            puuid: 原始PUUID

        Returns:
            匿名化后的哈希ID
        """
        if puuid in self.puuid_to_hash:
            return self.puuid_to_hash[puuid]

        # 生成新的哈希
        hash_id = self._hash_puuid(puuid)

        # 处理哈希冲突 (极其罕见)
        collision_counter = 0
        while hash_id in self.hash_to_puuid:
            collision_counter += 1
            hash_id = self._hash_puuid(f"{puuid}_{collision_counter}")
            if collision_counter > 100:
                raise RuntimeError(f"Too many hash collisions for PUUID: {puuid}")

        # 保存映射
        self.puuid_to_hash[puuid] = hash_id
        self.hash_to_puuid[hash_id] = puuid

        return hash_id

    def deanonymize_hash(self, hash_id: str) -> Optional[str]:
        """
        反匿名化哈希ID (仅在有salt的情况下可用)

        Args:
            hash_id: 匿名化的哈希ID

        Returns:
            原始PUUID或None
        """
        return self.hash_to_puuid.get(hash_id)

    def anonymize_batch(self, puuids: Set[str]) -> Dict[str, str]:
        """
        批量匿名化PUUID

        Args:
            puuids: PUUID集合

        Returns:
            PUUID -> 哈希ID的映射字典
        """
        mappings = {}
        new_mappings = 0

        for puuid in puuids:
            hash_id = self.anonymize_puuid(puuid)
            mappings[puuid] = hash_id

            if puuid not in self.puuid_to_hash:
                new_mappings += 1

        if new_mappings > 0:
            print(f"🔐 新增 {new_mappings} 个匿名化映射")
            self._save_mappings()

        return mappings

    def get_stats(self) -> Dict[str, int]:
        """获取匿名化统计信息"""
        return {
            'total_mappings': len(self.puuid_to_hash),
            'salt_length_bytes': len(self.salt),
            'hash_algorithm': 'SHA-256',
            'hash_length_chars': 16
        }

    def validate_mappings(self) -> bool:
        """验证映射关系的一致性"""
        if len(self.puuid_to_hash) != len(self.hash_to_puuid):
            print("❌ 映射数量不一致")
            return False

        for puuid, hash_id in self.puuid_to_hash.items():
            if self.hash_to_puuid.get(hash_id) != puuid:
                print(f"❌ 映射不一致: {puuid} -> {hash_id}")
                return False

        print(f"✅ 映射验证通过: {len(self.puuid_to_hash)} 个映射")
        return True

    def export_anonymized_puuids(self, output_file: str):
        """导出匿名化后的PUUID列表"""
        export_data = {
            'anonymous_ids': list(self.hash_to_puuid.keys()),
            'metadata': {
                'total_count': len(self.hash_to_puuid),
                'algorithm': 'SHA-256',
                'hash_length': 16,
                'export_date': '2024-09-28T00:00:00Z'
            }
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"📤 导出 {len(self.hash_to_puuid)} 个匿名ID到: {output_file}")

    def cleanup_orphaned_mappings(self, valid_puuids: Set[str]) -> int:
        """清理无效的映射关系"""
        orphaned_puuids = set(self.puuid_to_hash.keys()) - valid_puuids

        if not orphaned_puuids:
            print("✅ 没有发现无效映射")
            return 0

        # 移除无效映射
        for puuid in orphaned_puuids:
            hash_id = self.puuid_to_hash.pop(puuid)
            self.hash_to_puuid.pop(hash_id, None)

        # 保存更新后的映射
        self._save_mappings()

        print(f"🧹 清理了 {len(orphaned_puuids)} 个无效映射")
        return len(orphaned_puuids)


def main():
    """测试函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Player anonymization utility")
    parser.add_argument("--test-puuid", help="Test anonymization with a PUUID")
    parser.add_argument("--test-hash", help="Test deanonymization with a hash")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--validate", action="store_true", help="Validate mappings")
    parser.add_argument("--export", help="Export anonymized IDs to file")

    args = parser.parse_args()

    try:
        anonymizer = PlayerAnonymizer()

        if args.stats:
            stats = anonymizer.get_stats()
            print("📊 匿名化统计:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        if args.validate:
            anonymizer.validate_mappings()

        if args.test_puuid:
            hash_id = anonymizer.anonymize_puuid(args.test_puuid)
            print(f"PUUID {args.test_puuid[:8]}... → Hash {hash_id}")

        if args.test_hash:
            puuid = anonymizer.deanonymize_hash(args.test_hash)
            if puuid:
                print(f"Hash {args.test_hash} → PUUID {puuid[:8]}...")
            else:
                print(f"Hash {args.test_hash} 未找到对应PUUID")

        if args.export:
            anonymizer.export_anonymized_puuids(args.export)

    except Exception as e:
        print(f"错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())