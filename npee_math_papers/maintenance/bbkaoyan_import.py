#!/usr/bin/env python3
"""
bbkaoyan_data 数据导入工具

从 bbkaoyan_data 提取试卷数据，转换为本库的 YAML 格式。
"""
import json
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BbkQuestion:
    """bbkaoyan 题目数据结构"""
    question_id: int
    question_type: str  # 选择题、填空题、解答题
    section_index: int
    content: str
    options: Optional[List[Dict[str, str]]]  # 选择题的选项
    images: List[str]


@dataclass
class BbkPaper:
    """bbkaoyan 试卷数据结构"""
    paper_id: int
    title: str
    subject: str  # 数学一/二/三
    year: int
    organization: str
    series: str
    paper_no: int
    questions: List[BbkQuestion]


class BbkaoyanExtractor:
    """bbkaoyan_data 数据提取器"""

    def __init__(self, bbk_data_path: str):
        self.bbk_data_path = Path(bbk_data_path)
        self.db_path = self.bbk_data_path / "bbkaoyan.db"

        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {self.db_path}")

        # 建立数据库连接
        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def _map_subject(self, bbk_subject: str) -> str:
        """映射科目名称"""
        mapping = {
            'math1': 'math1',
            'math2': 'math2',
            'math3': 'math3',
            '数学一': 'math1',
            '数学二': 'math2',
            '数学三': 'math3',
        }
        return mapping.get(bbk_subject, bbk_subject)

    def _map_question_type(self, bbk_type: str) -> str:
        """映射题型"""
        mapping = {
            'choice': 'choice',
            'blank': 'fill',
            'solution': 'solution',
            '选择题': 'choice',
            '填空题': 'fill',
            '解答题': 'solution',
        }
        return mapping.get(bbk_type, bbk_type)

    def _get_series_info(self, provider_id: int, series_id: int) -> tuple:
        """获取机构和系列名称"""
        # 查询机构名称
        self.cursor.execute("SELECT name FROM dim_provider WHERE id = ?", (provider_id,))
        provider_row = self.cursor.fetchone()
        provider_name = provider_row[0] if provider_row else ''

        # 查询系列名称
        self.cursor.execute("SELECT name FROM dim_series WHERE id = ?", (series_id,))
        series_row = self.cursor.fetchone()
        series_name = series_row[0] if series_row else ''

        return provider_name, series_name

    def _map_series_key(self, provider: str, series: str) -> Optional[str]:
        """映射机构和系列到本库的 series_key"""
        # 构建映射规则
        series_map = {
            ('张宇', '八套卷'): 'zhangyu8',
            ('张宇', '四套卷'): 'zhangyu4',
            ('李林', '六套卷'): 'lilin6',
            ('余炳森', '五套卷'): 'yubingsen5',
            ('李艳芳', '三套卷'): 'liyanfang3',
            ('欧几里得', '三套卷'): 'euclid3',
            ('合工大', '超越十套卷'): 'chaoyue10',
        }
        return series_map.get((provider, series))

    def list_papers_for_series(self, series_key: str, year: int, subject: str) -> List[Dict]:
        """
        列出指定系列/年份/科目的所有试卷

        Returns:
            [{'paper_id': int, 'paper_no': int, 'question_count': int}, ...]
        """
        # 反向映射 series_key
        reverse_map = {
            'zhangyu8': ('张宇', '八套卷'),
            'zhangyu4': ('张宇', '四套卷'),
            'lilin6': ('李林', '六套卷'),
            'yubingsen5': ('余炳森', '五套卷'),
            'liyanfang3': ('李艳芳', '三套卷'),
            'euclid3': ('欧几里得', '三套卷'),
            'chaoyue10': ('合工大', '超越十套卷'),
        }

        if series_key not in reverse_map:
            return []

        provider, series = reverse_map[series_key]
        subject_code = self._map_subject(subject)

        # 查询试卷
        query = """
        SELECT p.id, p.set_number, p.declared_count
        FROM paper p
        JOIN dim_provider dp ON p.provider_id = dp.id
        JOIN dim_series ds ON p.series_id = ds.id
        WHERE p.subject = ? AND p.year = ?
          AND dp.name = ? AND ds.name = ?
        ORDER BY p.set_number
        """
        self.cursor.execute(query, (subject_code, year, provider, series))
        rows = self.cursor.fetchall()

        return [
            {'paper_id': row[0], 'paper_no': row[1], 'question_count': row[2]}
            for row in rows
        ]

    def extract_paper(self, paper_id: int) -> Optional[Dict[str, Any]]:
        """
        提取一套试卷的完整数据，转换为本库的 YAML 格式

        Returns:
            符合 schema 3.0 的试卷字典，可直接序列化为 YAML
        """
        # 查询试卷元信息
        self.cursor.execute("""
            SELECT id, title, subject, year, provider_id, series_id, set_number
            FROM paper WHERE id = ?
        """, (paper_id,))
        paper_row = self.cursor.fetchone()

        if not paper_row:
            return None

        paper_id, title, subject, year, provider_id, series_id, paper_no = paper_row
        provider, series = self._get_series_info(provider_id, series_id)
        series_key = self._map_series_key(provider, series)

        if not series_key:
            # 不在本库支持的系列范围内
            return None

        # 查询该卷的所有题目
        self.cursor.execute("""
            SELECT id, q_no, question_type, stem_latex,
                   option_a, option_b, option_c, option_d
            FROM question
            WHERE paper_id = ?
            ORDER BY q_no
        """, (paper_id,))
        question_rows = self.cursor.fetchall()

        # 构建题目数组
        questions = []
        for q_row in question_rows:
            q_id, q_no, q_type, stem, opt_a, opt_b, opt_c, opt_d = q_row
            section = self._map_question_type(q_type)

            # 清理 LaTeX 内容（移除 bbkaoyan 特有的标记）
            stem_clean = self._clean_latex(stem)

            question = {
                'number': q_no,
                'section': section,
                'points': self._estimate_points(section),
                'stem': {
                    'text': stem_clean.strip(),
                }
            }

            # 如果是选择题，添加选项
            if section == 'choice' and any([opt_a, opt_b, opt_c, opt_d]):
                choices = []
                for label, text in [('A', opt_a), ('B', opt_b), ('C', opt_c), ('D', opt_d)]:
                    if text:
                        choices.append({
                            'label': label,
                            'text': self._clean_latex(text).strip(),
                            'figures': []
                        })
                question['choices'] = choices

            questions.append(question)

        # 构建完整的试卷结构
        paper_data = {
            'schema_version': '3.0',
            'paper': {
                'series_key': series_key,
                'year': year,
                'subject': self._map_subject(subject),
                'paper_no': paper_no,
            },
            'questions': questions
        }

        return paper_data

    def _clean_latex(self, text: str) -> str:
        """清理 LaTeX 内容，移除不必要的标记"""
        if not text:
            return ''

        # 移除控制字符（ASCII 0-31 除了换行、制表符等有用字符）
        # 0x08 是退格符，经常出现在 bbkaoyan 数据中
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        # 移除 HTML 标记
        text = re.sub(r'<[^>]+>', '', text)

        # 移除 \displaystyle（在行内公式中通常不需要）
        text = text.replace(r'\displaystyle', '')

        # 移除多余的空白
        text = re.sub(r'\s+', ' ', text)

        # 移除选项末尾的句号（通常不需要）
        text = re.sub(r'\.\s*$', '', text)

        # 移除 \blank 占位符，替换为本库的格式
        text = text.replace(r'\blank', r'\underline{\qquad}')

        # 清理 \mathrm{d} 的空格
        text = re.sub(r'\\mathrm\{d\}\s*', r'\\mathrm{d}', text)

        # 清理积分符号周围的空格
        text = re.sub(r'\\int\s+', r'\\int ', text)

        # 转换 LaTeX 显示数学 \[...\] 为行内数学
        # \[...\] 是 LaTeX 标准的显示数学定界符，等价于 $$...$$
        # 题库规范要求只使用行内数学，所以转换为 $...$
        text = re.sub(r'\\\[(.*?)\\\]', r'$\1$', text, flags=re.DOTALL)

        # 使用 \dfrac 替代 \frac（在正文中）
        # 这里简化处理，实际可能需要更智能的判断
        text = text.replace(r'\frac{', r'\dfrac{')

        # 将数学模式中的中文标点转换为 ASCII 标点，并包裹 CJK 文本
        # 这是最关键的修复：bbkaoyan 数据库在公式中使用了全角标点和裸露的中文字符
        def replace_math_punctuation(match):
            math_content = match.group(1)
            # 全角逗号 → ASCII 逗号
            math_content = math_content.replace('，', ',')
            # 全角句号 → ASCII 句号
            math_content = math_content.replace('。', '.')
            # 全角分号 → ASCII 分号
            math_content = math_content.replace('；', ';')
            # 全角冒号 → ASCII 冒号
            math_content = math_content.replace('：', ':')

            # 包裹连续的 CJK 字符和标点为 \text{...}
            # 匹配一个或多个连续的中文字符/标点
            def wrap_cjk(m):
                cjk_text = m.group(0)
                # 如果已经在 \text{} 或其他文本命令中，跳过
                # 检查前面是否有未闭合的 \text{
                return f'\\text{{{cjk_text}}}'

            # 先处理已经在 \text{} 中的 CJK（避免重复包裹）
            # 保护已有的 \text{...} 块
            protected_segments = []
            def protect_text_blocks(m):
                idx = len(protected_segments)
                protected_segments.append(m.group(0))
                return f'__PROTECTED_{idx}__'

            math_content = re.sub(r'\\text\{[^}]+\}', protect_text_blocks, math_content)

            # 匹配中文字符、全角标点、顿号等（扩展 CJK 范围）
            # 包括 CJK 统一汉字 (U+4E00-9FFF)、扩展 A-F、兼容汉字等
            math_content = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef\u3000-\u303f]+', wrap_cjk, math_content)

            # 恢复被保护的 \text{} 块
            for idx, segment in enumerate(protected_segments):
                math_content = math_content.replace(f'__PROTECTED_{idx}__', segment)

            return f'${math_content}$'

        # 替换所有 $...$ 中的中文标点
        text = re.sub(r'\$([^$]+)\$', replace_math_punctuation, text)

        # 修复因紧邻数学模式产生的 $$ (block math)
        # bbkaoyan 中有 $formula$$,text$ 这样的模式，替换后变成 $$,
        # 需要在两个 $ 之间添加空格
        text = re.sub(r'\$\$', '$ $', text)

        return text.strip()

    def _estimate_points(self, section: str) -> int:
        """根据题型估算分值"""
        points_map = {
            'choice': 5,
            'fill': 5,
            'solution': 12,  # 解答题分值可能不同，暂定12
        }
        return points_map.get(section, 0)


class BbkaoyanConverter:
    """bbkaoyan 数据转换和导入控制器"""

    def __init__(self, bbk_data_path: str, local_store_path: str):
        self.extractor = BbkaoyanExtractor(bbk_data_path)
        self.local_store_path = Path(local_store_path)

    def convert_bundle(self, series_key: str, year: int, subject: str,
                      output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        转换一个完整的 bundle（系列+年份+科目）

        Returns:
            {'success': bool, 'converted': int, 'failed': int, 'papers': [...]}
        """
        papers_info = self.extractor.list_papers_for_series(series_key, year, subject)

        if not papers_info:
            return {
                'success': False,
                'error': f'未找到 {series_key}-{year}-{subject} 的试卷',
                'converted': 0,
                'failed': 0,
                'papers': []
            }

        converted = []
        failed = []

        for paper_info in papers_info:
            paper_id = paper_info['paper_id']
            paper_no = paper_info['paper_no']

            try:
                # 提取并转换
                paper_data = self.extractor.extract_paper(paper_id)

                if paper_data:
                    # 保存到临时目录（如果指定）
                    if output_dir:
                        bundle_name = f"{series_key}-{year}-{subject}"
                        bundle_dir = output_dir / bundle_name
                        bundle_dir.mkdir(parents=True, exist_ok=True)

                        output_file = bundle_dir / f"{paper_no}.yaml"
                        import yaml
                        with open(output_file, 'w', encoding='utf-8') as f:
                            yaml.dump(paper_data, f,
                                     allow_unicode=True,
                                     sort_keys=False,
                                     default_flow_style=False)

                    converted.append({
                        'paper_id': paper_id,
                        'paper_no': paper_no,
                        'questions': len(paper_data['questions'])
                    })
                else:
                    failed.append({'paper_id': paper_id, 'paper_no': paper_no})

            except Exception as e:
                failed.append({
                    'paper_id': paper_id,
                    'paper_no': paper_no,
                    'error': str(e)
                })

        return {
            'success': len(failed) == 0,
            'converted': len(converted),
            'failed': len(failed),
            'papers': converted,
            'errors': failed
        }

    def close(self):
        """关闭资源"""
        self.extractor.close()


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='bbkaoyan_data 数据导入工具')
    parser.add_argument('--bbk-path', required=True,
                       help='bbkaoyan_data 目录路径')
    parser.add_argument('--series', required=True,
                       help='系列 key，如 zhangyu8')
    parser.add_argument('--year', type=int, required=True,
                       help='年份，如 2024')
    parser.add_argument('--subject', required=True,
                       help='科目，如 math1')
    parser.add_argument('--output', required=True,
                       help='输出目录')

    args = parser.parse_args()

    converter = BbkaoyanConverter(args.bbk_path, '')
    result = converter.convert_bundle(
        args.series, args.year, args.subject,
        output_dir=Path(args.output)
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    converter.close()


if __name__ == '__main__':
    main()


    def _map_subject(self, bbk_subject: str) -> str:
        """映射科目名称"""
        mapping = {
            '数学一': 'math1',
            '数学二': 'math2',
            '数学三': 'math3',
        }
        return mapping.get(bbk_subject, bbk_subject)

    def _map_question_type(self, bbk_type: str) -> str:
        """映射题型"""
        mapping = {
            '选择题': 'choice',
            '填空题': 'fill',
            '解答题': 'solution',
        }
        return mapping.get(bbk_type, bbk_type)

    def _map_series(self, org: str, series: str) -> Optional[str]:
        """映射机构和系列到本库的 series_key"""
        # 构建映射规则
        series_map = {
            ('张宇', '八套卷'): 'zhangyu8',
            ('张宇', '四套卷'): 'zhangyu4',
            ('李林', '六套卷'): 'lilin6',
            ('余炳森', '五套卷'): 'yubingsen5',
            ('李艳芳', '三套卷'): 'liyanfang3',
            ('欧几里得', '三套卷'): 'euclid3',
            ('合工大', '超越十套卷'): 'chaoyue10',
        }
        return series_map.get((org, series))

    def extract_paper_by_path(self, paper_path: str) -> Optional[BbkPaper]:
        """
        从 papers 目录的 Markdown 文件提取试卷数据

        paper_path: 相对于 bbkaoyan_data/papers 的路径
        例如：数学一/模拟卷/张宇/八套卷/2024年第1套.md
        """
        full_path = self.bbk_data_path / "papers" / paper_path
        if not full_path.exists():
            return None

        # 解析路径提取元信息
        parts = Path(paper_path).parts
        if len(parts) < 5:
            return None

        subject = parts[0]
        paper_type = parts[1]  # 真题/模拟卷
        org = parts[2] if paper_type == '模拟卷' else None
        series = parts[3] if paper_type == '模拟卷' else None

        # 从文件名提取年份和套号
        filename = parts[-1].replace('.md', '')
        year_match = re.search(r'(\d{4})年', filename)
        no_match = re.search(r'第(\d+)套', filename)

        if not year_match or not no_match:
            return None

        year = int(year_match.group(1))
        paper_no = int(no_match.group(1))

        # 读取 Markdown 内容并解析题目
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        questions = self._parse_markdown_questions(content)

        return BbkPaper(
            paper_id=0,  # 从 MD 提取时没有 ID
            title=filename,
            subject=self._map_subject(subject),
            year=year,
            organization=org or '',
            series=series or '',
            paper_no=paper_no,
            questions=questions
        )

    def _parse_markdown_questions(self, content: str) -> List[BbkQuestion]:
        """解析 Markdown 内容中的题目"""
        questions = []

        # Markdown 格式：## 1. 题干...
        # 需要识别题号、题型、题干、选项等
        # 这里需要实现具体的解析逻辑

        # 简化版：按标题分割
        lines = content.split('\n')
        current_question = None
        current_content = []

        for line in lines:
            # 识别题号标题：## 1. 或 ### 选择题 1
            if line.startswith('##'):
                if current_question:
                    questions.append(current_question)
                    current_content = []

                # 提取题号
                match = re.search(r'(\d+)[\.、]', line)
                if match:
                    q_no = int(match.group(1))
                    current_question = BbkQuestion(
                        question_id=q_no,
                        question_type='',
                        section_index=q_no,
                        content='',
                        options=None,
                        images=[]
                    )
            elif current_question:
                current_content.append(line)

        if current_question:
            questions.append(current_question)

        return questions
