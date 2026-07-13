[English](README_en.md) | [中文](README.md)

# Obsidian Document Auto-Sync System

Automatically convert PDF, Word, Excel, HTML, and other documents into **Markdown** and sync them to your Obsidian Vault, without any manual intervention.

---

## Quick Start

### 1. Install Dependencies

```powershell
# Enter project directory
cd C:\Users\yangnianyong\obsidian-doc-sync

# Create a virtual environment (Recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install core dependencies
pip install watchdog pyyaml python-frontmatter loguru click apscheduler rich pypandoc openpyxl pandas markitdown

# Install Docling (High-quality PDF conversion, large size ~2GB)
pip install docling

# Optional: AI post-processing
pip install openai                    # OpenAI / DeepSeek
pip install google-generativeai       # Gemini
```

> **Pandoc** must be installed separately: https://pandoc.org/installing.html  
> After installation, restart your terminal and verify with `pandoc --version`

---

### 2. Configure config.yaml

Open [`config.yaml`](config.yaml) and **modify at least the following two paths**:

```yaml
paths:
  inbox: "D:/DocInbox"          # ← Your document folder (any path)
  vault: "D:/tools/bicv_obsidian"  # ← Auto-detected, confirm it's correct
```

**AI Post-processing Configuration (Optional):**

```yaml
ai:
  enabled: true              # Set to true to enable
  provider: "deepseek"       # openai | gemini | deepseek | ollama

  deepseek:
    api_key: "sk-xxx"        # Or set environment variable DEEPSEEK_API_KEY
```

---

### 3. Usage

```powershell
# Run manually (foreground, Ctrl+C to stop)
python sync_daemon.py start

# Detect available Vaults
python sync_daemon.py detect-vaults

# Full scan (process all existing files in Inbox)
python sync_daemon.py scan

# Check status and statistics
python sync_daemon.py status

# Manually retry failed files
python sync_daemon.py retry
```

### 4. Register as a Scheduled Task (Run on startup)

```powershell
# Run as Administrator
.\install_service.ps1

# Start immediately
Start-ScheduledTask -TaskName "ObsidianDocSync"

# Uninstall
.\install_service.ps1 -Uninstall
```

---

## System Architecture

```
DocInbox/
├── report.pdf        ─┐
├── meeting.docx       ├→ [watchdog listen] → [debounce queue]
└── budget.xlsx       ─┘        ↓
                          [SHA256 changes check]
                                ↓ Changed
                          [Converter Router]
                          ├── PDF  → Docling
                          ├── Word → Pandoc
                          ├── HTML → Pandoc
                          └── Excel → pandas
                                ↓
                          [AI Post-process (Optional)]
                          Summary / Tags / Category
                                ↓
                        Vault/Imported/
                        ├── PDF/report.md
                        ├── Word/meeting.md
                        └── Excel/budget.md
```

---

## Supported Formats

| Format | Extension | Conversion Engine |
|--------|-----------|-------------------|
| PDF | `.pdf` | **Docling** (Layout aware) → fallback to markitdown |
| Word | `.docx` `.doc` | **Pandoc** → Docling → fallback to markitdown |
| HTML | `.html` `.htm` | **Pandoc** → fallback to markitdown |
| Excel | `.xlsx` `.xls` | **pandas** (Multi-sheet support) |
| CSV | `.csv` | **pandas** |

### Add New Formats (Zero Intrusion)

Just create a new file in the `converters/` directory:

```python
# converters/pptx_converter.py
from converters.base import BaseConverter, ConvertResult

class PPTXConverter(BaseConverter):
    @property
    def supported_extensions(self): return ["pptx", "ppt"]

    def convert(self, source_path, output_dir, config):
        # Your conversion logic
        return ConvertResult.ok(markdown_content, "pptx")
```

Restart the daemon, and `.pptx` files will be handled automatically **without modifying any other code**.

---

## File Event Handling

| Event | Action |
|-------|--------|
| New File | Auto convert → Write to Vault |
| File Modified | SHA256 check → Re-convert if changed → Update MD |
| File Deleted | According to strategy: tag `source_deleted` / move to recycle bin / delete directly |
| File Renamed | MD file is renamed accordingly + Re-check content |

---

## Generated Markdown Example

```markdown
---
source_file: annual_report.pdf
source_path: D:/DocInbox/annual_report.pdf
source_hash: sha256:abc123...
converter: docling-pdf
converted_at: 2026-07-07T14:18:00+08:00
last_sync: 2026-07-07T14:18:00+08:00
summary: This report summarizes the financial status of 2025...
tags: [Finance, Annual Report, 2025]
category: Report
ai_processed: true
ai_provider: deepseek
---

# 2025 Annual Financial Report

...Content...
```

---

## AI Provider Selection

| Provider | Pros | Best For |
|----------|------|----------|
| **DeepSeek** | Best cost-performance, strong Chinese comprehension | Highly Recommended |
| **OpenAI** | Most stable quality | High-quality requirements |
| **Gemini** | Generous free tier | Light usage |
| **Ollama** | Completely offline, privacy-focused | Local deployment |

---

## FAQ

**Q: Docling installation is too slow?**  
A: You can use `markitdown` to verify the process first, and install Docling later for better quality.

**Q: Pandoc not found?**  
A: Restart your terminal after installation; or set the Word engine to `docling` in `config.yaml`.

**Q: No response after putting files in Inbox?**  
A: Check `logs/sync.log`; run `python sync_daemon.py status` to see the status.

**Q: How to switch Vault?**  
A: Modify `paths.vault` in `config.yaml` and restart the daemon.

---

## Changelog

### v1.1.0 - 2026-07-13
- **Optimization**: Updated logic for Excel, PDF, and Word converters.
- **Added**: Batch reset scripts such as `reset_all.py`, `reset_sfs_all.py`.
- **Testing**: Added conversion test cases like `test_docling_md.py`, `test_pandoc.py`.
- **Fix**: Improved database operations and Markdown generation sync logic.

### v1.0.1 - 2026-07-08
- **Added**: WPS-related batch conversion scripts (`convert_wps_batch.py`, etc.).
- **Added**: Internationalization support with English README.

### v1.0.0 - 2026-07-08
- **Initial Release**: Implemented automated multi-format document tracking via watchdog, AI processing, and Obsidian syncing.
