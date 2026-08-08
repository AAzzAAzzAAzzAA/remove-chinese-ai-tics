#!/usr/bin/env python3
"""Validate the internal structure of the remove-chinese-ai-tics skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


RULE_HEADING = re.compile(r"^###\s+([A-Z]\d{2})\s+(.+?)\s*$", re.M)
LEXICAL_HEADING = re.compile(r"^###\s+(L\d{2})\s+(.+?)\s*$", re.M)
EVALUATION_HEADING = re.compile(r"^###\s+(T\d{2})\s+(.+?)\s*$", re.M)
REFERENCE_LINK = re.compile(r"`(references/[A-Za-z0-9._/-]+\.md)`")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):", re.M)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--evaluation-suite", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    skill_dir = args.skill_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    skill_path = skill_dir / "SKILL.md"
    catalog_path = skill_dir / "references" / "pattern-catalog.md"
    lexical_path = skill_dir / "references" / "lexical-controls.md"
    creative_path = skill_dir / "references" / "creative-writing.md"
    interface_path = skill_dir / "agents" / "openai.yaml"
    if not skill_path.is_file():
        errors.append("missing SKILL.md")
    if not catalog_path.is_file():
        errors.append("missing references/pattern-catalog.md")
    if not lexical_path.is_file():
        errors.append("missing references/lexical-controls.md")
    if not creative_path.is_file():
        errors.append("missing references/creative-writing.md")
    if not interface_path.is_file():
        errors.append("missing agents/openai.yaml")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        raise SystemExit(1)

    skill_text = skill_path.read_text(encoding="utf-8")
    catalog_text = catalog_path.read_text(encoding="utf-8")
    lexical_text = lexical_path.read_text(encoding="utf-8")
    creative_text = creative_path.read_text(encoding="utf-8")

    frontmatter_parts = skill_text.split("---", 2)
    if len(frontmatter_parts) != 3 or frontmatter_parts[0].strip():
        errors.append("invalid SKILL.md frontmatter delimiters")
        frontmatter = ""
    else:
        frontmatter = frontmatter_parts[1]
    frontmatter_keys = FRONTMATTER_KEY.findall(frontmatter)
    if sorted(frontmatter_keys) != ["description", "name"]:
        errors.append("SKILL.md frontmatter must contain only name and description")
    name_match = re.search(r"^name:\s*([^\s]+)\s*$", frontmatter, re.M)
    if not name_match:
        errors.append("SKILL.md frontmatter missing name")
        skill_name = ""
    else:
        skill_name = name_match.group(1)
        if skill_name != skill_dir.name:
            errors.append(f"skill folder and frontmatter name differ: {skill_dir.name} != {skill_name}")
    if not re.search(r"^description:\s*\S.+$", frontmatter, re.M):
        errors.append("SKILL.md frontmatter missing description")
    if interface_path.is_file() and skill_name:
        interface_text = interface_path.read_text(encoding="utf-8")
        for required in ("display_name:", "short_description:", "default_prompt:", f"${skill_name}"):
            if required not in interface_text:
                errors.append(f"agents/openai.yaml missing {required}")
    rules = RULE_HEADING.findall(catalog_text)
    ids = [rule_id for rule_id, _ in rules]
    duplicates = sorted({rule_id for rule_id in ids if ids.count(rule_id) > 1})
    if duplicates:
        errors.append(f"duplicate rule ids: {', '.join(duplicates)}")
    if len(rules) < 60:
        errors.append(f"pattern catalog unexpectedly small: {len(rules)} rules")

    sections = re.split(r"(?=^###\s+[A-Z]\d{2}\s+)", catalog_text, flags=re.M)
    for section in sections:
        match = RULE_HEADING.match(section)
        if not match:
            continue
        rule_id = match.group(1)
        for required in ("**信号：**", "**边界：**", "**修复：**"):
            if required not in section:
                errors.append(f"{rule_id} missing {required}")

    lexical_rules = LEXICAL_HEADING.findall(lexical_text)
    lexical_ids = [rule_id for rule_id, _ in lexical_rules]
    lexical_duplicates = sorted({rule_id for rule_id in lexical_ids if lexical_ids.count(rule_id) > 1})
    if lexical_duplicates:
        errors.append(f"duplicate lexical family ids: {', '.join(lexical_duplicates)}")
    if len(lexical_rules) < 18:
        errors.append(f"lexical family catalog unexpectedly small: {len(lexical_rules)} rules")
    lexical_sections = re.split(r"(?=^###\s+L\d{2}\s+)", lexical_text, flags=re.M)
    for section in lexical_sections:
        match = LEXICAL_HEADING.match(section)
        if not match:
            continue
        rule_id = match.group(1)
        for required in ("**搜索成员：**", "**成簇信号：**", "**保护：**", "**修复：**"):
            if required not in section:
                errors.append(f"{rule_id} missing {required}")

    references = sorted(set(REFERENCE_LINK.findall(skill_text)))
    for relative in references:
        if not (skill_dir / relative).is_file():
            errors.append(f"missing referenced file: {relative}")

    reference_files = sorted((skill_dir / "references").glob("*.md"))
    for path in reference_files:
        text = path.read_text(encoding="utf-8")
        if len(text.splitlines()) > 100 and "## 目录" not in text:
            errors.append(f"long reference missing table of contents: {path.name}")

    evaluation_path = args.evaluation_suite
    if evaluation_path is None:
        repository_evaluation = skill_dir.parent / "tests" / "evaluation-suite.md"
        if repository_evaluation.is_file():
            evaluation_path = repository_evaluation
    evaluation_cases: list[tuple[str, str]] = []
    if evaluation_path is not None:
        evaluation_path = evaluation_path.expanduser().resolve()
        if not evaluation_path.is_file():
            errors.append(f"missing evaluation suite: {evaluation_path}")
        else:
            evaluation_text = evaluation_path.read_text(encoding="utf-8")
            evaluation_cases = EVALUATION_HEADING.findall(evaluation_text)
            evaluation_ids = [case_id for case_id, _ in evaluation_cases]
            evaluation_duplicates = sorted(
                {case_id for case_id in evaluation_ids if evaluation_ids.count(case_id) > 1}
            )
            if evaluation_duplicates:
                errors.append(f"duplicate evaluation ids: {', '.join(evaluation_duplicates)}")
            if len(evaluation_cases) < 50:
                errors.append(f"evaluation suite unexpectedly small: {len(evaluation_cases)} cases")
            for required in ("## 目录", "## 运行方式", "## 回归通过标准"):
                if required not in evaluation_text:
                    errors.append(f"evaluation suite missing {required}")

    forbidden_literals = (
        "AGE-SECRET-KEY-",
        "BEGIN OPENSSH PRIVATE KEY",
    )
    distributable_files = [skill_path, *reference_files]
    if evaluation_path is not None and evaluation_path.is_file():
        distributable_files.append(evaluation_path)
    for path in distributable_files:
        text = path.read_text(encoding="utf-8")
        for literal in forbidden_literals:
            if literal in text:
                errors.append(f"sensitive research literal in {path.name}: {literal}")

    if "判断文本由人还是模型写" not in skill_text:
        errors.append("missing authorship-classification boundary")
    if "不得通过故意写错字" not in skill_text:
        errors.append("missing anti-simulation boundary")
    if "严格口癖规则" not in skill_text:
        errors.append("missing strict hard-control boundary")
    if "不做同义词漂白" not in skill_text:
        errors.append("missing anti-synonym-bleaching boundary")
    for required in ("verbatim_protect", "semantic_locks", "cleared", "protected_verbatim", "blocked_by_invariant", "primary_id"):
        if required not in lexical_text:
            errors.append(f"lexical controls missing {required}")
    for required in (
        "创意写作优先级",
        "建立连续性账本",
        "将通用规则应用到创意文本",
        "互动创作附加约束",
        "创意文本终检",
    ):
        if required not in creative_text:
            errors.append(f"creative writing module missing {required}")

    result = {
        "ok": not errors,
        "skill_dir": str(skill_dir),
        "pattern_rules": len(rules),
        "lexical_families": len(lexical_rules),
        "evaluation_cases": len(evaluation_cases),
        "references": references,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
