#!/usr/bin/env python3
"""
将转换后的 YAML 文件批量入库

使用 npee_math_papers 的核心 API 将转换好的 YAML 落盘到题库。
"""
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any

# 导入本库的核心服务
from npee_math_papers.service import NpeeService


class ConvertedIngestor:
    """转换数据入库器"""

    def __init__(self, converted_dir: Path, store_root: Path):
        self.converted_dir = converted_dir
        self.service = NpeeService.create(store_root)

    def list_converted_bundles(self) -> List[str]:
        """列出已转换的 bundle"""
        return [d.name for d in self.converted_dir.iterdir() if d.is_dir()]

    def ingest_bundle(self, bundle_name: str, replace: bool = False) -> Dict[str, Any]:
        """
        入库一个 bundle 的所有试卷

        Args:
            bundle_name: bundle 目录名，如 'zhangyu8-2024-math1'
            replace: 是否覆盖已存在的试卷

        Returns:
            {'success': bool, 'ingested': int, 'failed': int, 'details': [...]}
        """
        bundle_dir = self.converted_dir / bundle_name
        if not bundle_dir.exists():
            return {
                'success': False,
                'error': f'Bundle 目录不存在: {bundle_name}',
                'ingested': 0,
                'failed': 0
            }

        yaml_files = sorted(bundle_dir.glob('*.yaml'))
        if not yaml_files:
            return {
                'success': False,
                'error': f'Bundle 目录为空: {bundle_name}',
                'ingested': 0,
                'failed': 0
            }

        ingested = []
        failed = []

        for yaml_file in yaml_files:
            try:
                # 读取 YAML
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    paper_data = yaml.safe_load(f)

                # 调用服务入库
                result = self.service.extraction.ingest_document(
                    document=paper_data,
                    replace=replace
                )

                ingested.append({
                    'file': yaml_file.name,
                    'paper_no': paper_data['paper']['paper_no'],
                    'questions': len(paper_data['questions']),
                    'result': result
                })

            except Exception as e:
                failed.append({
                    'file': yaml_file.name,
                    'error': str(e)
                })

        return {
            'success': len(failed) == 0,
            'ingested': len(ingested),
            'failed': len(failed),
            'details': ingested,
            'errors': failed
        }

    def ingest_all(self, replace: bool = False) -> Dict[str, Any]:
        """
        批量入库所有转换好的 bundle

        Args:
            replace: 是否覆盖已存在的试卷

        Returns:
            汇总结果
        """
        bundles = self.list_converted_bundles()
        total = len(bundles)

        print(f"发现 {total} 个 bundle 需要入库")
        if replace:
            print("模式：覆盖已存在的试卷")
        else:
            print("模式：跳过已存在的试卷")

        results = []

        for i, bundle_name in enumerate(bundles, 1):
            print(f"[{i}/{total}] 入库 {bundle_name}...")

            result = self.ingest_bundle(bundle_name, replace=replace)
            results.append({
                'bundle': bundle_name,
                **result
            })

            if result['success']:
                print(f"  OK: {result['ingested']} papers")
            else:
                print(f"  FAIL: {result.get('error', '')}, {result['failed']} errors")
                # 显示前3个错误
                for err in result.get('errors', [])[:3]:
                    print(f"    - {err['file']}: {err['error']}")

        # 汇总统计
        total_ingested = sum(r['ingested'] for r in results)
        total_failed = sum(r['failed'] for r in results)
        success_count = sum(1 for r in results if r['success'])

        summary = {
            'total_bundles': total,
            'success_bundles': success_count,
            'total_papers_ingested': total_ingested,
            'total_papers_failed': total_failed,
            'results': results
        }

        print(f"\n入库完成！")
        print(f"  成功 bundle: {success_count}/{total}")
        print(f"  入库试卷: {total_ingested}")
        print(f"  失败试卷: {total_failed}")

        return summary


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='批量入库转换后的 YAML')
    parser.add_argument('--converted-dir',
                       default='.npee-math-papers/staging/converted',
                       help='转换后的 YAML 目录')
    parser.add_argument('--store-root',
                       default='.npee-math-papers',
                       help='题库根目录')
    parser.add_argument('--replace', action='store_true',
                       help='覆盖已存在的试卷')
    parser.add_argument('--bundle',
                       help='只入库指定的 bundle')

    args = parser.parse_args()

    converted_dir = Path(args.converted_dir)
    store_root = Path(args.store_root)

    ingestor = ConvertedIngestor(converted_dir, store_root)

    if args.bundle:
        result = ingestor.ingest_bundle(args.bundle, replace=args.replace)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        summary = ingestor.ingest_all(replace=args.replace)
        # 保存结果
        result_file = store_root / "staging" / "ingest_results.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"结果保存至: {result_file}")


if __name__ == '__main__':
    main()
