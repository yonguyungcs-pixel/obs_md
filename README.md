# Obsidian 文档自动同步系统

将 PDF、Word、Excel、HTML 等文档**自动转换为 Markdown** 并同步到 Obsidian Vault，全程无需人工干预。

---

## 快速开始

### 1. 安装依赖

```powershell
# 进入项目目录
cd C:\Users\yangnianyong\obsidian-doc-sync

# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\Activate.ps1

# 安装依赖（核心必装）
pip install watchdog pyyaml python-frontmatter loguru click apscheduler rich pypandoc openpyxl pandas markitdown

# 安装 Docling（PDF 高质量转换，较大约 2GB）
pip install docling

# 可选：AI 后处理
pip install openai                    # OpenAI / DeepSeek
pip install google-generativeai       # Gemini
```

> **Pandoc** 需单独安装：https://pandoc.org/installing.html  
> 安装后重启终端，`pandoc --version` 验证

---

### 2. 配置 config.yaml

打开 [`config.yaml`](config.yaml)，**至少修改以下两个路径**：

```yaml
paths:
  inbox: "D:/DocInbox"          # ← 你放文档的目录（任意路径）
  vault: "D:/tools/bicv_obsidian"  # ← 已自动检测，确认即可
```

**AI 后处理配置（可选）：**

```yaml
ai:
  enabled: true              # 改为 true 启用
  provider: "deepseek"       # openai | gemini | deepseek | ollama

  deepseek:
    api_key: "sk-xxx"        # 或设置环境变量 DEEPSEEK_API_KEY
```

---

### 3. 启动

```powershell
# 手动运行（前台，Ctrl+C 停止）
python sync_daemon.py start

# 查看自动检测到的 Vault
python sync_daemon.py detect-vaults

# 全量扫描（处理 Inbox 内所有已有文件）
python sync_daemon.py scan

# 查看状态统计
python sync_daemon.py status

# 手动重试失败文件
python sync_daemon.py retry
```

### 4. 注册为计划任务（开机自动启动）

```powershell
# 以管理员权限运行
.\install_service.ps1

# 立即启动
Start-ScheduledTask -TaskName "ObsidianDocSync"

# 卸载
.\install_service.ps1 -Uninstall
```

---

## 系统架构

```
DocInbox/
├── report.pdf        ─┐
├── meeting.docx       ├→ [watchdog 监听] → [防抖队列]
└── budget.xlsx       ─┘        ↓
                           [SHA256 变更检测]
                                ↓ 内容有变化
                           [转换器路由]
                           ├── PDF  → Docling
                           ├── Word → Pandoc
                           ├── HTML → Pandoc
                           └── Excel → pandas
                                ↓
                           [AI 后处理（可选）]
                           摘要 / Tags / 分类
                                ↓
                        Vault/Imported/
                        ├── PDF/report.md
                        ├── Word/meeting.md
                        └── Excel/budget.md
```

---

## 支持格式

| 格式 | 扩展名 | 转换引擎 |
|------|--------|---------|
| PDF | `.pdf` | **Docling**（布局感知）→ markitdown 降级 |
| Word | `.docx` `.doc` | **Pandoc** → Docling → markitdown 降级 |
| HTML | `.html` `.htm` | **Pandoc** → markitdown 降级 |
| Excel | `.xlsx` `.xls` | **pandas**（多 Sheet 支持）|
| CSV | `.csv` | **pandas** |

### 扩展新格式（零侵入）

只需在 `converters/` 目录下新建一个文件：

```python
# converters/pptx_converter.py
from converters.base import BaseConverter, ConvertResult

class PPTXConverter(BaseConverter):
    @property
    def supported_extensions(self): return ["pptx", "ppt"]

    def convert(self, source_path, output_dir, config):
        # 你的转换逻辑
        return ConvertResult.ok(markdown_content, "pptx")
```

重启守护进程，`.pptx` 文件将自动被处理，**无需修改任何其他代码**。

---

## 文件事件处理

| 事件 | 行为 |
|------|------|
| 新增文件 | 自动转换 → 写入 Vault |
| 修改文件 | SHA256 检测 → 有变化时重新转换 → 更新 MD |
| 删除文件 | 按策略：标记 `source_deleted` / 移入回收 / 直接删除 |
| 重命名 | MD 文件跟随重命名 + 重新检查内容 |

---

## 生成的 Markdown 示例

```markdown
---
source_file: annual_report.pdf
source_path: D:/DocInbox/annual_report.pdf
source_hash: sha256:abc123...
converter: docling-pdf
converted_at: 2026-07-07T14:18:00+08:00
last_sync: 2026-07-07T14:18:00+08:00
summary: 本报告总结了2025年度财务状况...
tags: [财务, 年报, 2025]
category: 报告
ai_processed: true
ai_provider: deepseek
---

# 2025 年度财务报告

...正文内容...
```

---

## AI 提供商选择

| 提供商 | 优点 | 适用场景 |
|--------|------|---------|
| **DeepSeek** | 性价比最高，中文理解强 | 推荐首选 |
| **OpenAI** | 质量最稳定 | 对质量要求高 |
| **Gemini** | 免费额度较大 | 轻度使用 |
| **Ollama** | 完全离线，隐私安全 | 本地部署 |

---

## 常见问题

**Q: Docling 安装太慢？**  
A: 可先用 `markitdown` 验证流程，后续再安装 Docling 获得更好质量。

**Q: Pandoc 找不到？**  
A: 安装后重启终端；或在 `config.yaml` 中设置 Word 引擎为 `docling`。

**Q: 文件放入 Inbox 后没有反应？**  
A: 检查 `logs/sync.log`；运行 `python sync_daemon.py status` 查看状态。

**Q: 如何切换 Vault？**  
A: 修改 `config.yaml` 中的 `paths.vault`，重启守护进程。
