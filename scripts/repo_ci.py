#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用仓库检查 —— 所有仓库共用这一份（由中央仓库 repo-ci 提供）。

设计原则：**默认宽松**。目的是「任何仓库都能直接启用，不会一上来满屏红」，
所以默认只做**几乎不可能误报**的检查；严格的检查由目标仓库用 `.ci.json` 主动开启。

默认（总是执行）：
  1. 密钥扫描           —— 命中即失败（这是底线，任何仓库都该有）
  2. JSON 语法
  3. Python 语法        —— compile() 不落盘
  4. YAML 语法          —— 装了 PyYAML 才查，没有就跳过（不因为缺依赖而炸）

可选（在仓库根放 `.ci.json` 开启）：
  {
    "markdown_links": true,                  # 检查 md 相对链接是否失效
    "require_files": ["README.md", "LICENSE"] # 这些文件必须存在
  }

用法：
  python3 repo_ci.py [仓库根目录]        # 默认当前工作目录
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
errors: list[str] = []

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".zip", ".gz",
               ".mp3", ".mp4", ".mov", ".pdf", ".woff", ".woff2", ".ttf", ".lock"}

SECRETS = [
    (re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"), "OpenRouter key"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub PAT"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"), "Anthropic key"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "OpenAI 风格 key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "私钥"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"), "Slack token"),
]


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def walk():
    for p in sorted(ROOT.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def read_text(p: Path):
    if p.suffix.lower() in SKIP_SUFFIX:
        return None
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def main() -> int:
    cfg = {}
    cfg_path = ROOT / ".ci.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f".ci.json 解析失败 —— {e}")

    self_name = Path(__file__).name

    # 1 + 2 + 3：一次遍历里做完密钥扫描、JSON、Python
    for p in walk():
        text = read_text(p)
        if text is None or p.name == self_name:
            continue

        for rx, label in SECRETS:
            m = rx.search(text)
            if m:
                errors.append(f"{rel(p)}：疑似泄漏 {label}（{m.group(0)[:12]}…）")

        if p.suffix.lower() == ".json":
            try:
                json.loads(text)
            except Exception as e:
                errors.append(f"{rel(p)}：JSON 解析失败 —— {e}")
        elif p.suffix.lower() == ".py":
            try:
                compile(text, str(p), "exec")
            except SyntaxError as e:
                errors.append(f"{rel(p)}：Python 语法错误 —— 第 {e.lineno} 行 {e.msg}")

    # 4：YAML（缺 PyYAML 就跳过，不因此失败）
    yml_files = [p for p in walk() if p.suffix.lower() in (".yml", ".yaml")]
    if yml_files:
        try:
            import yaml  # type: ignore
        except ImportError:
            print("提示：未装 PyYAML，跳过 YAML 检查")
        else:
            for p in yml_files:
                text = read_text(p)
                if text is None:
                    continue
                try:
                    yaml.safe_load(text)
                except Exception as e:
                    errors.append(f"{rel(p)}：YAML 解析失败 —— {str(e)[:120]}")

    # 可选：markdown 相对链接
    if cfg.get("markdown_links"):
        LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+?)\)")
        for p in walk():
            if p.suffix.lower() != ".md":
                continue
            text = read_text(p)
            if text is None:
                continue
            for target in LINK.findall(text):
                if target.startswith(("http://", "https://", "mailto:", "#", "<")):
                    continue
                if not (p.parent / target).resolve().exists():
                    errors.append(f"{rel(p)}：相对链接失效 -> {target}")

    # 可选：必备文件
    for name in cfg.get("require_files") or []:
        if not (ROOT / name).exists():
            errors.append(f"缺必备文件：{name}")

    if errors:
        print(f"仓库检查未通过（{len(errors)} 项）：\n")
        for e in errors:
            print("  ✗", e)
        return 1

    print(f"仓库检查通过：{rel(ROOT) or '.'} —— 密钥/JSON/Python/YAML 均 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
