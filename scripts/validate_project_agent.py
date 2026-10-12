#!/usr/bin/env python3
"""Validate project-agent-bootstrap output and legacy-file migration hints."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


RULE_FILE_NAMES = {"agents.md", "agent.md"}
MANAGED_START = "<!-- project-agent-bootstrap:managed:start -->"
MANAGED_END = "<!-- project-agent-bootstrap:managed:end -->"
REQUIRED_AGENT_HEADINGS = (
    "## 1. 项目背景/需求概述",
    "## 2. 项目技术框架",
    "## 3. 项目目录结构",
    "## 4. 项目管理规则",
    "## 5. 代码设计与编写原则",
)
LINKED_WORKSPACE_HEADING = "## 6. 关联工作目录"
LINKED_WORKSPACE_COLUMNS = ("名称", "路径", "用途", "规则来源", "维护方式")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def check_required_file(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"缺少文件：{path}")
        return ""
    try:
        return read_text(path)
    except UnicodeDecodeError as exc:
        errors.append(f"文件不是 UTF-8 文本：{path} ({exc})")
        return ""


def resolve_rule_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.name.lower() in RULE_FILE_NAMES
    )


def check_markers(
    content: str,
    label: str,
    errors: list[str],
    warnings: list[str],
    strict: bool,
) -> None:
    start_count = content.count(MANAGED_START)
    end_count = content.count(MANAGED_END)
    valid = (
        start_count == 1
        and end_count == 1
        and content.index(MANAGED_START) < content.index(MANAGED_END)
    )
    if valid:
        return
    message = f"{label}缺少有效托管区标记，运行技能时需要迁移或补充标记"
    if strict:
        errors.append(message)
    else:
        warnings.append(message)


def check_linked_workspaces(
    content: str,
    label: str,
    errors: list[str],
    warnings: list[str],
    strict_markers: bool,
) -> None:
    """Check the optional linked-workspace section without touching external paths."""
    if LINKED_WORKSPACE_HEADING not in content:
        if strict_markers and MANAGED_START in content and MANAGED_END in content:
            errors.append(f"{label}缺少关联工作目录章节")
        return

    start = content.index(LINKED_WORKSPACE_HEADING)
    next_heading = re.search(r"^##\s+", content[start + len(LINKED_WORKSPACE_HEADING) :], re.MULTILINE)
    end = start + len(LINKED_WORKSPACE_HEADING) + next_heading.start() if next_heading else len(content)
    section = content[start:end]
    if "无已登记关联工作目录" in section:
        return

    for column in LINKED_WORKSPACE_COLUMNS:
        if column not in section:
            errors.append(f"{label}关联工作目录章节缺少字段：{column}")

    table_rows = [
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    data_rows = [
        row
        for row in table_rows[1:]
        if not re.fullmatch(r"\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|", row)
    ]
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < len(LINKED_WORKSPACE_COLUMNS):
            errors.append(f"{label}关联工作目录表格存在字段不足的行：{row}")
    if data_rows and not any(
        marker in section
        for marker in ("外部 `AGENTS.md`", "继承父项目规则", "待确认")
    ):
        warnings.append(f"{label}关联工作目录表格未明确规则来源状态")


def check_agent(
    root: Path,
    errors: list[str],
    warnings: list[str],
    strict_markers: bool,
) -> None:
    candidates = resolve_rule_files(root)
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        errors.append(f"存在多个规则文件候选，请指定主文件：{names}")
        return
    path = candidates[0] if candidates else root / "AGENTS.md"
    content = check_required_file(path, errors)
    for heading in REQUIRED_AGENT_HEADINGS:
        if heading not in content:
            errors.append(f"{path.name} 缺少章节：{heading}")
    if content:
        check_markers(content, path.name, errors, warnings, strict_markers)
        check_linked_workspaces(content, path.name, errors, warnings, strict_markers)


def check_progress(
    root: Path,
    errors: list[str],
    warnings: list[str],
    strict_markers: bool,
) -> None:
    content = check_required_file(root / "progress.md", errors)
    if content and not re.search(r"^版本号：.*$", content, re.MULTILINE):
        errors.append("progress.md 缺少顶部版本号配置")
    if content and not re.search(r"^当前需求编号：.*$", content, re.MULTILINE):
        errors.append("progress.md 缺少顶部需求编号配置")
    if content and "## 项目进度记录" not in content:
        errors.append("progress.md 缺少项目进度记录章节")
    if content:
        check_markers(content, "progress.md", errors, warnings, strict_markers)
    version_sections = list(re.finditer(r"^## 版本 .+$", content, re.MULTILINE))
    for index, match in enumerate(version_sections):
        end = version_sections[index + 1].start() if index + 1 < len(version_sections) else len(content)
        section = content[match.start() : end]
        if "### 提交 " not in section and "### 记录 " not in section:
            errors.append(f"版本章节没有提交或同步记录：{match.group(0)}")
        if "- commitId：" not in section:
            errors.append(f"版本章节没有 commitId：{match.group(0)}")


def check_docs(
    root: Path,
    errors: list[str],
    warnings: list[str],
    strict_markers: bool,
) -> None:
    docs = root / "docs"
    if not docs.is_dir():
        errors.append(f"缺少 docs 目录：{docs}")
        return
    inventory = docs / "文档清单.md"
    content = check_required_file(inventory, errors)
    if content and not re.search(r"文档路径|文档名称", content):
        errors.append("docs/文档清单.md 未包含文档路径或文档名称字段")
    if content and not re.search(r"\.md|\.docx|\.pdf|\.txt", content, re.IGNORECASE):
        warnings.append("文档清单暂未发现常见文档路径，请确认清单是否完整")
    if content:
        check_markers(content, "docs/文档清单.md", errors, warnings, strict_markers)


def check_gitignore(root: Path, errors: list[str], require_docs_ignore: bool) -> None:
    content = check_required_file(root / ".gitignore", errors)
    entries = {
        line.strip().replace("\\", "/")
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for expected in ("AGENTS.md", "progress.md"):
        if expected not in entries:
            errors.append(f".gitignore 缺少：{expected}")
    if require_docs_ignore and (root / "docs").is_dir() and "docs/" not in entries and "docs" not in entries:
        errors.append(".gitignore 缺少：docs/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate project-agent-bootstrap output")
    parser.add_argument("--root", default=".", help="项目根目录，默认为当前目录")
    parser.add_argument(
        "--docs-created",
        action="store_true",
        help="docs/ 是本次新建时，要求 .gitignore 包含 docs/",
    )
    parser.add_argument(
        "--strict-managed-markers",
        action="store_true",
        help="要求 AGENTS.md、progress.md 和文档清单具备完整托管标记",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"项目根目录不存在：{root}", file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    check_agent(root, errors, warnings, args.strict_managed_markers)
    check_progress(root, errors, warnings, args.strict_managed_markers)
    check_docs(root, errors, warnings, args.strict_managed_markers)
    check_gitignore(root, errors, args.docs_created)

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"校验失败：{len(errors)} 个错误，{len(warnings)} 个提醒")
        return 1
    print(f"校验通过：{root}")
    if warnings:
        print(f"存在 {len(warnings)} 个提醒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
