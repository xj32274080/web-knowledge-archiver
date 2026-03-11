---
name: web-knowledge-archiver
description: "Archive a webpage or WeChat public article into reusable knowledge assets. Trigger when the user says things like 归档这个链接, 归档这个网页, 保存这个网页, 保存这个链接, 把这个公众号文章归档下来, 把这个链接沉淀到 Obsidian, 整理成 NotebookLM 资料, or otherwise gives a URL and wants a durable package with PDF, cleaned Markdown正文, selected or all local images, plus export into Obsidian and/or a NotebookLM-ready folder."
---

# Web Knowledge Archiver

Archive a URL into a durable local knowledge package rather than a one-off summary.

## Strong triggers

Use this skill aggressively when the user provides a URL and asks for any of these outcomes:

- “归档这个链接”
- “归档这个网页”
- “保存这个网页”
- “保存这个链接”
- “把这个公众号文章归档下来”
- “把这个链接沉淀到 Obsidian”
- “整理成 NotebookLM 资料”

Also use it when the user clearly wants:

- PDF 留档
- 正文抽取
- 图片本地化保存
- Obsidian 知识沉淀
- NotebookLM 导入材料准备

## Default workflow

1. Run `scripts/archive_url.py "<url>"`.
2. Let the script choose the extraction method:
   - Generic webpages: prefer Jina Reader output for clean正文, with Scrapling HTML fallback.
   - WeChat public articles: prefer Scrapling HTML capture, then convert with `html2text`.
3. Always keep three asset types when possible:
   - PDF snapshot
   - Markdown note
   - Selected local images in `note.assets/`
4. Save into Obsidian first. If the user also wants NotebookLM, mirror the generated files into a NotebookLM-ready directory.

## Image policy

- `--image-mode curated` is the default. It keeps a focused subset of likely important content images.
- `--image-mode all` keeps every detected article image.
- Images are saved as local files, not remote links, because remote image URLs often expire.
- In curated mode, prefer content images over logos, avatars, icons, QR codes, and decorative assets.

## Output shape

The script writes:

- `YYYY-MM-DD-title.md`
- `YYYY-MM-DD-title.assets/`
- `YYYY-MM-DD-title.pdf` when PDF capture succeeds

The Markdown note includes source URL, capture date, 正文, and local image embeds.

## Defaults

See `references/defaults.md` for the default Obsidian vault and NotebookLM staging location.

## When to override defaults

- If the user wants a different vault, pass `--obsidian-root`.
- If the user wants a different Obsidian subdirectory, pass `--obsidian-subdir`.
- If the user wants NotebookLM-ready exports, pass `--notebooklm-root`.
- If the user wants all article images instead of a curated subset, pass `--image-mode all`.

## Failure handling

- If a webpage extractor returns an anti-bot page, fall back to another method before giving up.
- If PDF generation fails, still save Markdown + images.
- If NotebookLM CLI is unavailable, still prepare the import folder rather than blocking the task.
