#!/usr/bin/env python3
"""
Archive a URL into PDF + cleaned Markdown + selected local images.

Supports:
- Generic webpages via Jina Reader with HTML/browser fallback
- WeChat public articles via Scrapling + html2text
- Obsidian-friendly output (`note.md` + `note.pdf` + `note.assets/`)
- Optional NotebookLM-ready mirror directory
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import html2text
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from scrapling import Fetcher


PLAYWRIGHT_CHROME = Path(
    r"C:\Users\Lenovo\AppData\Local\ms-playwright\chromium-1208\chrome-win64\chrome.exe"
)
DEFAULT_OBSIDIAN_ROOT = Path(r"D:\codex-work\myproject\Daxuan-study-system")
DEFAULT_OBSIDIAN_SUBDIR = Path("学习资料") / "网页归档"
DEFAULT_NOTEBOOKLM_ROOT = Path.home() / "Documents" / "NotebookLM Imports"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
JINA_PREFIX = "https://r.jina.ai/http://"
WECHAT_HOST = "mp.weixin.qq.com"
DROP_IMAGE_TOKENS = ("avatar", "logo", "icon", "emoji", "qrcode", "qr", "banner")


@dataclass
class ExtractionResult:
    title: str
    markdown: str
    article_html: str
    final_url: str
    source_method: str


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = re.sub(r"[\\/:*?\"<>|]+", "-", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.rstrip(".")
    return normalized[:120] or "untitled"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_wechat_url(url: str) -> bool:
    return WECHAT_HOST in urlparse(url).netloc.lower()


def is_probably_challenge(text: str) -> bool:
    markers = (
        "环境异常",
        "请稍后",
        "Just a moment",
        "checking your browser",
        "requiring CAPTCHA",
        "Access denied",
    )
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def html_to_markdown(html: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0
    converter.single_line_break = False
    return converter.handle(html).strip()


def strip_html_noise(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "footer", "nav", "aside"]):
        tag.decompose()
    return str(soup)


def extract_title_from_html(html: str, fallback: str = "") -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.text.strip():
        return soup.title.text.strip()
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return fallback or "Untitled"


def fetch_jina_markdown(url: str) -> tuple[str, str]:
    target = JINA_PREFIX + url.replace("https://", "").replace("http://", "")
    response = requests.get(target, timeout=60, headers=REQUEST_HEADERS)
    response.raise_for_status()
    text = response.text
    if is_probably_challenge(text):
        raise RuntimeError("Jina returned anti-bot or challenge content")
    if "Markdown Content:" not in text:
        raise RuntimeError("Jina output missing markdown payload")
    title_match = re.search(r"Title:\s*(.+)", text)
    markdown = text.split("Markdown Content:", 1)[1].strip()
    title = title_match.group(1).strip() if title_match else ""
    return title, markdown


def fetch_scrapling_html(url: str) -> tuple[str, str]:
    response = Fetcher(auto_match=False).get(url, verify=False, timeout=45)
    html = response.html_content or ""
    if not html:
        raise RuntimeError("Scrapling returned empty HTML")
    if is_probably_challenge(html):
        raise RuntimeError("Scrapling returned challenge content")
    return extract_title_from_html(html), html


def choose_main_content(soup: BeautifulSoup, wechat: bool) -> BeautifulSoup:
    selectors = (
        ["#js_content", "#img-content", "article", ".rich_media_content"]
        if wechat
        else ["article", "main", "[role='main']", ".post-content", ".entry-content", ".article-content"]
    )
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node
    return soup.body or soup


def extract_images(article_node: BeautifulSoup, base_url: str) -> list[dict]:
    images: list[dict] = []
    for img in article_node.find_all("img"):
        src = (img.get("data-src") or img.get("data-original") or img.get("src") or "").strip()
        if not src:
            continue
        images.append(
            {
                "src": urljoin(base_url, src),
                "alt": (img.get("alt") or "").strip(),
                "class_name": " ".join(img.get("class") or []),
                "width": str(img.get("width") or ""),
                "height": str(img.get("height") or ""),
            }
        )
    return images


def score_image(image: dict, index: int) -> int:
    src = image["src"].lower()
    alt = image["alt"].strip()
    class_name = image["class_name"].lower()
    score = 0
    if any(token in src for token in ("mmbiz.qpic.cn", "wx", "miro.medium.com", "substackcdn")):
        score += 2
    if alt:
        score += 1
    if image["width"] or image["height"]:
        score += 1
    if index < 4:
        score += 1
    if any(token in src or token in class_name for token in DROP_IMAGE_TOKENS):
        score -= 4
    return score


def select_images(images: list[dict], image_mode: str) -> list[dict]:
    if image_mode == "all":
        return images
    selected = []
    seen = set()
    for index, image in enumerate(images):
        src = image["src"]
        if not src or src in seen:
            continue
        seen.add(src)
        if score_image(image, index) >= 1:
            selected.append(image)
    return selected[:12]


def infer_extension(url: str, content_type: str = "") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
        return suffix
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    return mapping.get(content_type.lower(), ".img")


def download_image(url: str, destination: Path) -> bool:
    try:
        response = requests.get(url, timeout=45, headers=REQUEST_HEADERS)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if "image" not in content_type:
            return False
        final_destination = destination.with_suffix(infer_extension(url, content_type))
        final_destination.write_bytes(response.content)
        return True
    except Exception:
        return False


def save_pdf(url: str, pdf_path: Path) -> bool:
    if not PLAYWRIGHT_CHROME.exists():
        return False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=str(PLAYWRIGHT_CHROME),
            )
            page = browser.new_page(viewport={"width": 1440, "height": 2200})
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(3000)
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            browser.close()
        return pdf_path.exists()
    except Exception:
        return False


def build_frontmatter(data: dict) -> str:
    lines = ["---"]
    for key, value in data.items():
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines)


def extract_content(url: str) -> ExtractionResult:
    wechat = is_wechat_url(url)
    if wechat:
        title, html = fetch_scrapling_html(url)
        article = choose_main_content(BeautifulSoup(html, "html.parser"), wechat=True)
        cleaned_html = strip_html_noise(str(article))
        markdown = html_to_markdown(cleaned_html)
        return ExtractionResult(
            title=title,
            markdown=markdown,
            article_html=cleaned_html,
            final_url=url,
            source_method="scrapling-wechat",
        )

    try:
        title, markdown = fetch_jina_markdown(url)
        page_title, html = fetch_scrapling_html(url)
        article = choose_main_content(BeautifulSoup(html, "html.parser"), wechat=False)
        cleaned_html = strip_html_noise(str(article))
        return ExtractionResult(
            title=title or page_title,
            markdown=markdown,
            article_html=cleaned_html,
            final_url=url,
            source_method="jina+scrapling",
        )
    except Exception:
        title, html = fetch_scrapling_html(url)
        article = choose_main_content(BeautifulSoup(html, "html.parser"), wechat=False)
        cleaned_html = strip_html_noise(str(article))
        markdown = html_to_markdown(cleaned_html)
        return ExtractionResult(
            title=title,
            markdown=markdown,
            article_html=cleaned_html,
            final_url=url,
            source_method="scrapling-fallback",
        )


def write_note(
    result: ExtractionResult,
    obsidian_dir: Path,
    note_name: str,
    notebooklm_root: Path | None,
    pdf_path: Path | None,
    image_mode: str,
) -> dict:
    note_path = obsidian_dir / f"{note_name}.md"
    assets_dir = ensure_dir(obsidian_dir / f"{note_name}.assets")

    article_node = BeautifulSoup(result.article_html, "html.parser")
    images = extract_images(article_node, result.final_url)
    selected_images = select_images(images, image_mode=image_mode)

    local_refs: list[tuple[dict, Path]] = []
    for index, image in enumerate(selected_images, start=1):
        destination = assets_dir / f"image-{index:02d}.img"
        if download_image(image["src"], destination):
            actual_path = next(
                (
                    candidate
                    for candidate in assets_dir.glob(f"image-{index:02d}.*")
                    if candidate.is_file()
                ),
                None,
            )
            if actual_path:
                local_refs.append((image, actual_path))

    appendix: list[str] = []
    if local_refs:
        appendix.extend(["## 关键图片", ""])
        for image, image_path in local_refs:
            rel = f"{assets_dir.name}/{image_path.name}"
            appendix.append(f"![{image['alt'] or image_path.stem}]({rel})")
            appendix.append("")

    frontmatter = build_frontmatter(
        {
            "title": result.title,
            "source": result.final_url,
            "captured": datetime.now().strftime("%Y-%m-%d"),
            "method": result.source_method,
        }
    )
    body = [
        frontmatter,
        "",
        f"# {result.title}",
        "",
        "## 原文链接",
        "",
        f"[{result.final_url}]({result.final_url})",
        "",
        "## 正文",
        "",
        result.markdown.strip(),
    ]
    if appendix:
        body.extend(["", *appendix])
    note_path.write_text("\n".join(body).strip() + "\n", encoding="utf-8")

    notebooklm_path = None
    if notebooklm_root:
        nlm_dir = ensure_dir(notebooklm_root / note_name)
        shutil.copy2(note_path, nlm_dir / note_path.name)
        if pdf_path and pdf_path.exists():
            shutil.copy2(pdf_path, nlm_dir / pdf_path.name)
        if assets_dir.exists():
            target_assets = nlm_dir / assets_dir.name
            if target_assets.exists():
                shutil.rmtree(target_assets)
            shutil.copytree(assets_dir, target_assets)
        notebooklm_path = nlm_dir

    return {
        "note_path": str(note_path),
        "pdf_path": str(pdf_path) if pdf_path and pdf_path.exists() else "",
        "assets_dir": str(assets_dir),
        "saved_images": [str(path) for _, path in local_refs],
        "notebooklm_path": str(notebooklm_path) if notebooklm_path else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive a webpage/article into Obsidian-ready files.")
    parser.add_argument("url", help="The URL to archive")
    parser.add_argument("--obsidian-root", default=str(DEFAULT_OBSIDIAN_ROOT))
    parser.add_argument("--obsidian-subdir", default=str(DEFAULT_OBSIDIAN_SUBDIR))
    parser.add_argument("--notebooklm-root", default="")
    parser.add_argument(
        "--image-mode",
        choices=["curated", "all"],
        default="curated",
        help="curated = keep likely important content images only; all = keep every detected article image",
    )
    args = parser.parse_args()

    notebooklm_root = Path(args.notebooklm_root) if args.notebooklm_root else None
    result = extract_content(args.url)

    note_name = f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(result.title)}"
    obsidian_dir = ensure_dir(Path(args.obsidian_root) / Path(args.obsidian_subdir))
    pdf_path = obsidian_dir / f"{note_name}.pdf"
    pdf_ok = save_pdf(result.final_url, pdf_path)

    saved = write_note(
        result=result,
        obsidian_dir=obsidian_dir,
        note_name=note_name,
        notebooklm_root=notebooklm_root,
        pdf_path=pdf_path if pdf_ok else None,
        image_mode=args.image_mode,
    )

    payload = {
        "title": result.title,
        "url": result.final_url,
        "method": result.source_method,
        **saved,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
