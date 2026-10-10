# repo-ci

一个**可复用**的 GitHub Actions 工作流：给名下所有仓库提供同一套基础检查，不用每个仓库各存一份脚本。

## 它查什么

**默认（总是执行，设计成几乎不会误报）**

| 检查 | 说明 |
|---|---|
| 🔑 **密钥扫描** | OpenRouter / Anthropic / OpenAI / GitHub PAT / AWS / Slack / 私钥 —— 命中即失败 |
| JSON 语法 | 所有 `*.json` 能否解析 |
| Python 语法 | `compile()` 检查，不落盘 |
| YAML 语法 | 所有 `*.yml` / `*.yaml`（装了 PyYAML 才查） |

**可选（在仓库根放 `.ci.json` 开启）**

```json
{
  "markdown_links": true,
  "require_files": ["README.md", "LICENSE"]
}
```

## 怎么用

在目标仓库新建 `.github/workflows/ci.yml`：

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  check:
    uses: Joey1444/repo-ci/.github/workflows/check.yml@main
```

推送即生效。私有仓库也能调用（公开仓库里的 reusable workflow 可被私有仓库引用）。

## 为什么默认宽松

一上来就满屏红，人就会把 CI 关掉。所以默认只做**任何仓库都该过、且几乎不可能误报**的检查；
严格项由仓库自己 `.ci.json` 主动开。

## 本地先跑一遍

```bash
curl -fsSL -o /tmp/repo_ci.py \
  https://raw.githubusercontent.com/Joey1444/repo-ci/main/scripts/repo_ci.py
python3 /tmp/repo_ci.py .          # 检查当前目录
```

推之前先在本地跑，别推上去撞运气。

## License

MIT
