# web-knowledge-archiver

Archive a webpage or WeChat public article into durable local knowledge assets: PDF snapshot, cleaned Markdown正文, and local images for long-term use in Obsidian or NotebookLM.

把网页或公众号文章归档成可长期复用的本地知识包：PDF 留档、Markdown 正文、本地图片，并沉淀到 Obsidian 或 NotebookLM 准备目录。

## Install

```bash
npx skills add xj32274080/web-knowledge-archiver
```

## What it does

- Saves a PDF snapshot for long-term reference
- Extracts cleaned Markdown正文 automatically
- Chooses extractor by source type
  - Generic webpages: prefer Jina Reader, then fall back to Scrapling
  - WeChat public articles: use Scrapling + html2text
- Downloads images as local files instead of fragile remote links
- Supports two image modes
  - `curated`: keep likely important content images only
  - `all`: keep every detected article image
- Saves into Obsidian first and can mirror to a NotebookLM-ready import folder

## 中文说明

- 自动根据链接类型选择正文提取方案
- 普通网页优先走 `Jina Reader`，失败后回退 `Scrapling`
- 公众号文章优先走 `Scrapling + html2text`
- 图片默认下载到本地，不依赖容易失效的热链
- 默认使用“精选图片”模式，只保留更像正文内容图的图片
- 也支持“全部图片”模式，保留正文区域检测到的全部图片

## Main command

```bash
python scripts/archive_url.py "<url>"
```

## Common examples

Default archive:

```bash
python scripts/archive_url.py "https://example.com"
```

Archive and keep all article images:

```bash
python scripts/archive_url.py "https://example.com" --image-mode all
```

Archive and prepare a NotebookLM import folder:

```bash
python scripts/archive_url.py "https://example.com" --notebooklm-root "%USERPROFILE%\\Documents\\NotebookLM Imports"
```

## Output structure

The skill writes:

- `YYYY-MM-DD-title.md`
- `YYYY-MM-DD-title.assets/`
- `YYYY-MM-DD-title.pdf`

Typical structure:

```text
学习资料/
  网页归档/
    2026-03-11-文章标题.md
    2026-03-11-文章标题.assets/
      image-01.png
      image-02.jpg
```

## Trigger phrases

Natural trigger phrases include:

- `归档这个链接`
- `归档这个网页`
- `保存这个网页`
- `保存这个链接`
- `把这个公众号文章归档下来`
- `把这个链接沉淀到 Obsidian`
- `整理成 NotebookLM 资料`

## Files

- [SKILL.md](./SKILL.md)
- [scripts/archive_url.py](./scripts/archive_url.py)
- [references/defaults.md](./references/defaults.md)

## Notes

- PDF generation depends on a local Playwright browser being available
- NotebookLM integration currently prepares import-ready folders; it does not upload automatically
- Image selection in `curated` mode is heuristic, not vision-model based

## License

MIT
