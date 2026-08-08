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
REFERENCE_LINK = re.compile(r"`(references/[A-Za-z0-9._/-]+\.md)`")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
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
    if not skill_path.is_file():
        errors.append("missing SKILL.md")
    if not catalog_path.is_file():
        errors.append("missing references/pattern-catalog.md")
    if not lexical_path.is_file():
        errors.append("missing references/lexical-controls.md")
    if not creative_path.is_file():
        errors.append("missing references/creative-writing.md")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        raise SystemExit(1)

    skill_text = skill_path.read_text(encoding="utf-8")
    catalog_text = catalog_path.read_text(encoding="utf-8")
    lexical_text = lexical_path.read_text(encoding="utf-8")
    creative_text = creative_path.read_text(encoding="utf-8")
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

    forbidden_literals = (
        "AGE-SECRET-KEY-",
        "BEGIN OPENSSH PRIVATE KEY",
    )
    distributable_files = [skill_path, *sorted((skill_dir / "references").glob("*.md"))]
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
        "references": references,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
