#!/usr/bin/env python3
"""
Multi-Format Output Pipeline
构建Parquet+DuckDB多格式输出管道，支持高效存储和查询
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import asdict
import shutil

class MultiFormatOutputPipeline:
    """多格式输出管道"""

    def __init__(self,
                 silver_dir: str = "data/silver",
                 gold_dir: str = "data/gold",
                 formats: List[str] = None):

        self.silver_dir = Path(silver_dir)
        self.gold_dir = Path(gold_dir)
        self.gold_dir.mkdir(parents=True, exist_ok=True)

        # 支持的输出格式
        self.formats = formats or ["parquet", "duckdb", "json", "csv"]

        # 创建格式特定目录
        for fmt in self.formats:
            (self.gold_dir / fmt).mkdir(parents=True, exist_ok=True)

        # DuckDB连接
        self.db_path = self.gold_dir / "duckdb" / "analytics.duckdb"
        self.conn = None

        print(f"🔄 初始化多格式输出管道")
        print(f"📁 Silver层: {self.silver_dir}")
        print(f"📁 Gold层: {self.gold_dir}")
        print(f"📦 支持格式: {self.formats}")

    def _init_duckdb(self):
        """初始化DuckDB连接"""
        if self.conn is None:
            self.conn = duckdb.connect(str(self.db_path))
            print(f"🔗 DuckDB连接: {self.db_path}")

    def _close_duckdb(self):
        """关闭DuckDB连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def load_silver_data(self) -> Dict[str, List[Dict]]:
        """加载Silver层数据"""
        print("📊 加载Silver层数据...")

        data_sources = {}

        # 加载SCD2维表数据
        dimensions_dir = self.silver_dir / "dimensions"
        if dimensions_dir.exists():
            for dim_file in dimensions_dir.glob("*.json"):
                if "summary" not in dim_file.name:
                    with open(dim_file, 'r') as f:
                        data = json.load(f)

                    table_name = dim_file.stem
                    data_sources[table_name] = data.get('records', [])
                    print(f"  📋 维表 {table_name}: {len(data_sources[table_name])} 条记录")

        # 加载事实表数据
        facts_dir = self.silver_dir / "facts"
        if facts_dir.exists():
            fact_records = []
            for fact_file in facts_dir.glob("*.json"):
                if "summary" not in fact_file.name:
                    with open(fact_file, 'r') as f:
                        data = json.load(f)

                    records = data.get('records', [])
                    fact_records.extend(records)

            if fact_records:
                data_sources['fact_match_performance'] = fact_records
                print(f"  📊 事实表 fact_match_performance: {len(fact_records)} 条记录")

        # 加载增强事实表数据
        enhanced_facts_dir = self.silver_dir / "enhanced_facts"
        if enhanced_facts_dir.exists():
            enhanced_records = []
            for fact_file in enhanced_facts_dir.glob("*.json"):
                if "governance" not in fact_file.name:
                    with open(fact_file, 'r') as f:
                        data = json.load(f)

                    records = data.get('records', [])
                    enhanced_records.extend(records)

            if enhanced_records:
                data_sources['enhanced_fact_match_performance'] = enhanced_records
                print(f"  🛡️ 增强事实表: {len(enhanced_records)} 条记录")

        return data_sources

    def convert_to_parquet(self, data_sources: Dict[str, List[Dict]]):
        """转换为Parquet格式"""
        print("\n📦 转换为Parquet格式...")

        parquet_dir = self.gold_dir / "parquet"

        for table_name, records in data_sources.items():
            if not records:
                continue

            try:
                # 转换为DataFrame
                df = pd.DataFrame(records)

                # 优化数据类型
                df = self._optimize_dataframe_types(df, table_name)

                # 保存为Parquet
                parquet_file = parquet_dir / f"{table_name}.parquet"
                df.to_parquet(parquet_file, index=False, compression='snappy')

                # 验证文件
                file_size = parquet_file.stat().st_size / 1024 / 1024  # MB
                print(f"  ✅ {table_name}.parquet: {len(records)} 条记录, {file_size:.1f}MB")

            except Exception as e:
                print(f"  ❌ {table_name} Parquet转换失败: {e}")

    def _optimize_dataframe_types(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """优化DataFrame数据类型以减少存储空间"""

        # 通用优化规则
        for col in df.columns:
            if df[col].dtype == 'object':
                # 尝试转换为数值类型
                if df[col].str.match(r'^\d+$').all() if not df[col].isna().all() else False:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                # 尝试转换为类别类型（对于重复值多的列）
                elif df[col].nunique() / len(df) < 0.5:
                    df[col] = df[col].astype('category')

            # 优化整数类型
            elif df[col].dtype in ['int64']:
                if df[col].min() >= 0:
                    if df[col].max() <= 255:
                        df[col] = df[col].astype('uint8')
                    elif df[col].max() <= 65535:
                        df[col] = df[col].astype('uint16')
                    elif df[col].max() <= 4294967295:
                        df[col] = df[col].astype('uint32')
                else:
                    if df[col].min() >= -128 and df[col].max() <= 127:
                        df[col] = df[col].astype('int8')
                    elif df[col].min() >= -32768 and df[col].max() <= 32767:
                        df[col] = df[col].astype('int16')

            # 优化浮点类型
            elif df[col].dtype == 'float64':
                df[col] = pd.to_numeric(df[col], downcast='float')

        # 表特定优化
        if table_name.startswith('fact_'):
            # 事实表特定优化
            boolean_cols = ['win', 'game_ended_early', 'surrender',
                           'anonymization_validated', 'pii_detection_passed', 'gdpr_compliant']
            for col in boolean_cols:
                if col in df.columns:
                    df[col] = df[col].astype('bool')

            # 类别列优化
            category_cols = ['tier', 'position', 'champion_name', 'game_mode', 'risk_level']
            for col in category_cols:
                if col in df.columns:
                    df[col] = df[col].astype('category')

        return df

    def load_into_duckdb(self, data_sources: Dict[str, List[Dict]]):
        """加载数据到DuckDB"""
        print("\n🦆 加载数据到DuckDB...")

        self._init_duckdb()

        for table_name, records in data_sources.items():
            if not records:
                continue

            try:
                # 创建DataFrame
                df = pd.DataFrame(records)
                df = self._optimize_dataframe_types(df, table_name)

                # 删除表（如果存在）
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")

                # 创建表并插入数据
                self.conn.register(f"{table_name}_df", df)
                self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {table_name}_df")

                # 验证数据
                row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"  ✅ {table_name}: {row_count} 条记录")

            except Exception as e:
                print(f"  ❌ {table_name} DuckDB加载失败: {e}")

    def create_analytics_views(self):
        """创建分析视图"""
        print("\n📈 创建分析视图...")

        if not self.conn:
            return

        # 创建性能分析视图
        performance_view = """
        CREATE OR REPLACE VIEW player_performance_summary AS
        SELECT
            tier,
            position,
            champion_name,
            COUNT(*) as games_played,
            AVG(kills) as avg_kills,
            AVG(deaths) as avg_deaths,
            AVG(assists) as avg_assists,
            AVG(kda_ratio) as avg_kda,
            AVG(gold_per_minute) as avg_gpm,
            AVG(cs_per_minute) as avg_cspm,
            AVG(vision_score_per_minute) as avg_vspm,
            AVG(damage_per_minute) as avg_dpm,
            SUM(CASE WHEN win THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
        FROM fact_match_performance
        GROUP BY tier, position, champion_name
        HAVING games_played >= 10
        ORDER BY tier, avg_kda DESC
        """

        try:
            self.conn.execute(performance_view)
            print("  ✅ player_performance_summary 视图")
        except Exception as e:
            print(f"  ❌ 性能分析视图创建失败: {e}")

        # 创建治理质量视图（如果有增强数据）
        if self.conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'enhanced_fact_match_performance'").fetchone()[0] > 0:
            governance_view = """
            CREATE OR REPLACE VIEW data_quality_summary AS
            SELECT
                tier,
                patch_version,
                COUNT(*) as total_records,
                AVG(data_quality_score) as avg_quality_score,
                AVG(completeness_score) as avg_completeness,
                AVG(accuracy_score) as avg_accuracy,
                AVG(consistency_score) as avg_consistency,
                SUM(CASE WHEN gdpr_compliant THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as compliance_rate,
                SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as low_risk_rate
            FROM enhanced_fact_match_performance
            GROUP BY tier, patch_version
            ORDER BY patch_version, tier
            """

            try:
                self.conn.execute(governance_view)
                print("  ✅ data_quality_summary 视图")
            except Exception as e:
                print(f"  ❌ 治理质量视图创建失败: {e}")

        # 创建补丁分析视图
        patch_analysis_view = """
        CREATE OR REPLACE VIEW patch_performance_analysis AS
        SELECT
            patch_version,
            tier,
            COUNT(*) as games_in_patch,
            AVG(game_duration_minutes) as avg_game_duration,
            AVG(kills + assists) as avg_kp,
            AVG(gold_per_minute) as avg_gpm,
            COUNT(DISTINCT champion_name) as unique_champions,
            SUM(CASE WHEN kills >= 10 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as carry_game_rate
        FROM fact_match_performance
        GROUP BY patch_version, tier
        ORDER BY patch_version, tier
        """

        try:
            self.conn.execute(patch_analysis_view)
            print("  ✅ patch_performance_analysis 视图")
        except Exception as e:
            print(f"  ❌ 补丁分析视图创建失败: {e}")

    def export_to_csv(self, data_sources: Dict[str, List[Dict]]):
        """导出为CSV格式"""
        print("\n📄 导出为CSV格式...")

        csv_dir = self.gold_dir / "csv"

        for table_name, records in data_sources.items():
            if not records:
                continue

            try:
                df = pd.DataFrame(records)
                csv_file = csv_dir / f"{table_name}.csv"
                df.to_csv(csv_file, index=False, encoding='utf-8')

                file_size = csv_file.stat().st_size / 1024 / 1024  # MB
                print(f"  ✅ {table_name}.csv: {len(records)} 条记录, {file_size:.1f}MB")

            except Exception as e:
                print(f"  ❌ {table_name} CSV导出失败: {e}")

    def export_analytics_results(self):
        """导出分析结果"""
        print("\n📊 导出分析结果...")

        if not self.conn:
            return

        # 获取所有视图
        views = self.conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_type = 'VIEW'
        """).fetchall()

        results_dir = self.gold_dir / "analytics"
        results_dir.mkdir(exist_ok=True)

        for (view_name,) in views:
            try:
                # 导出为CSV
                result_df = self.conn.execute(f"SELECT * FROM {view_name}").df()
                csv_file = results_dir / f"{view_name}.csv"
                result_df.to_csv(csv_file, index=False)

                # 导出为JSON
                json_file = results_dir / f"{view_name}.json"
                result_dict = result_df.to_dict('records')
                with open(json_file, 'w') as f:
                    json.dump({
                        'view_name': view_name,
                        'exported_at': datetime.now(timezone.utc).isoformat(),
                        'record_count': len(result_dict),
                        'data': result_dict
                    }, f, indent=2, default=str)

                print(f"  ✅ {view_name}: {len(result_dict)} 条记录")

            except Exception as e:
                print(f"  ❌ {view_name} 分析结果导出失败: {e}")

    def generate_metadata(self, data_sources: Dict[str, List[Dict]]):
        """生成元数据"""
        print("\n📋 生成元数据...")

        metadata = {
            'pipeline_metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'pipeline_version': '1.0',
                'formats_supported': self.formats,
                'source_data_summary': {}
            },
            'table_schemas': {},
            'data_statistics': {},
            'quality_summary': {}
        }

        # 收集表结构和统计信息
        for table_name, records in data_sources.items():
            if not records:
                continue

            # 数据统计
            metadata['pipeline_metadata']['source_data_summary'][table_name] = {
                'record_count': len(records),
                'sample_record': records[0] if records else {}
            }

            # 字段统计
            df = pd.DataFrame(records)
            field_stats = {}

            for col in df.columns:
                field_stats[col] = {
                    'type': str(df[col].dtype),
                    'non_null_count': int(df[col].count()),
                    'null_count': int(df[col].isnull().sum()),
                    'unique_values': int(df[col].nunique())
                }

                # 数值字段额外统计
                if df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                    field_stats[col].update({
                        'min': float(df[col].min()) if not df[col].isna().all() else None,
                        'max': float(df[col].max()) if not df[col].isna().all() else None,
                        'mean': float(df[col].mean()) if not df[col].isna().all() else None
                    })

            metadata['table_schemas'][table_name] = field_stats

        # 数据质量摘要（如果有治理数据）
        if 'enhanced_fact_match_performance' in data_sources:
            enhanced_df = pd.DataFrame(data_sources['enhanced_fact_match_performance'])

            metadata['quality_summary'] = {
                'total_records': len(enhanced_df),
                'avg_data_quality_score': float(enhanced_df['data_quality_score'].mean()),
                'gdpr_compliance_rate': float(enhanced_df['gdpr_compliant'].mean() * 100),
                'risk_distribution': enhanced_df['risk_level'].value_counts().to_dict()
            }

        # 保存元数据
        metadata_file = self.gold_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        print(f"  ✅ 元数据: {metadata_file}")

    def run_multi_format_pipeline(self):
        """运行完整的多格式输出管道"""
        print("🚀 开始多格式输出管道...")

        try:
            # 1. 加载Silver层数据
            data_sources = self.load_silver_data()

            if not data_sources:
                print("❌ 未找到Silver层数据")
                return

            # 2. 转换为不同格式
            if "parquet" in self.formats:
                self.convert_to_parquet(data_sources)

            if "duckdb" in self.formats:
                self.load_into_duckdb(data_sources)
                self.create_analytics_views()
                self.export_analytics_results()

            if "csv" in self.formats:
                self.export_to_csv(data_sources)

            # 3. 生成元数据
            self.generate_metadata(data_sources)

            # 4. 生成摘要报告
            self._generate_summary_report(data_sources)

            print("✅ 多格式输出管道完成!")

        except Exception as e:
            print(f"💥 多格式输出管道失败: {e}")
            raise
        finally:
            self._close_duckdb()

    def _generate_summary_report(self, data_sources: Dict[str, List[Dict]]):
        """生成摘要报告"""
        print("\n📋 生成摘要报告...")

        total_records = sum(len(records) for records in data_sources.values())

        summary = {
            'multi_format_pipeline_summary': {
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'total_tables_processed': len(data_sources),
                'total_records_processed': total_records,
                'output_formats': self.formats,
                'output_directory': str(self.gold_dir)
            },
            'table_summary': {
                table_name: len(records)
                for table_name, records in data_sources.items()
            },
            'format_outputs': {
                'parquet': list((self.gold_dir / "parquet").glob("*.parquet")) if "parquet" in self.formats else [],
                'duckdb': str(self.db_path) if "duckdb" in self.formats else None,
                'csv': list((self.gold_dir / "csv").glob("*.csv")) if "csv" in self.formats else [],
                'analytics': list((self.gold_dir / "analytics").glob("*")) if "duckdb" in self.formats else []
            }
        }

        # 计算文件大小
        total_size = 0
        for fmt_dir in [self.gold_dir / fmt for fmt in self.formats]:
            if fmt_dir.exists():
                for file_path in fmt_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size

        summary['storage_summary'] = {
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'avg_compression_ratio': 'N/A'  # 需要与原始JSON比较
        }

        summary_file = self.gold_dir / "pipeline_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"  ✅ 管道摘要: {summary_file}")
        print(f"  📊 处理表数: {len(data_sources)}")
        print(f"  📋 总记录数: {total_records:,}")
        print(f"  💾 输出大小: {summary['storage_summary']['total_size_mb']:.1f}MB")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Format Output Pipeline")
    parser.add_argument("--silver-dir", default="data/silver",
                       help="Silver层数据目录")
    parser.add_argument("--gold-dir", default="data/gold",
                       help="Gold层输出目录")
    parser.add_argument("--formats", nargs='+',
                       choices=['parquet', 'duckdb', 'csv', 'json'],
                       default=['parquet', 'duckdb', 'csv'],
                       help="输出格式")

    args = parser.parse_args()

    try:
        pipeline = MultiFormatOutputPipeline(
            silver_dir=args.silver_dir,
            gold_dir=args.gold_dir,
            formats=args.formats
        )

        pipeline.run_multi_format_pipeline()
        return 0

    except Exception as e:
        print(f"💥 管道执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())