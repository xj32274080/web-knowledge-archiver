# web-knowledge-archiver

Archive a webpage or WeChat public article into reusable knowledge assets with a PDF snapshot, cleaned Markdown正文, and local images for long-term use in Obsidian or NotebookLM.

## Install

```bash
npx skills add xj32274080/web-knowledge-archiver
```

## What it does

- Saves a PDF snapshot for long-term reference
- Extracts cleaned Markdown正文 automatically
- Chooses extractor by source type:
  - Generic webpages: prefer Jina Reader, then fall back to Scrapling
  - WeChat public articles: use Scrapling + html2text
- Downloads images as local files instead of keeping fragile remote links
- Supports two image modes:
  - `curated`: keep likely important content images only
  - `all`: keep every detected article image
- Saves into Obsidian first and can mirror to a NotebookLM-ready import folder

## Default output

The skill writes:

- `YYYY-MM-DD-title.md`
- `YYYY-MM-DD-title.assets/`
- `YYYY-MM-DD-title.pdf`

## Main command

```bash
python scripts/archive_url.py "<url>"
```

Optional arguments:

```bash
python scripts/archive_url.py "<url>" --image-mode all --notebooklm-root "%USERPROFILE%\\Documents\\NotebookLM Imports"
```

## Default trigger phrases

- `归档这个链接`
- `归档这个网页`
- `保存这个网页`
- `把这个公众号文章归档下来`
- `把这个链接沉淀到 Obsidian`
- `整理成 NotebookLM 资料`

## Files

- [SKILL.md](./SKILL.md)
- [scripts/archive_url.py](./scripts/archive_url.py)
- [references/defaults.md](./references/defaults.md)

## License

MIT
