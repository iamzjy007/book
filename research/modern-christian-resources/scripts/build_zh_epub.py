#!/usr/bin/env python3
"""Build Lori / DYDI EPUB files from consolidated .txt sources (English and Chinese)."""
from __future__ import annotations

import argparse
import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
STYLE = (
    "body{font-family:serif;line-height:1.8;margin:5%;}"
    "h1{font-size:1.45em;line-height:1.5;}"
    "h2{font-size:1.2em;}"
    "p{text-align:justify;margin:0 0 0.8em;}"
    "a{overflow-wrap:anywhere;} "
    ".meta{font-size:0.85em;color:#555;} "
    ".cover{text-align:center;padding-top:20%;} "
    ".cover p{text-align:center;} "
    "nav ol{padding-left:1.5em;} "
    "nav li{margin-bottom:0.6em;}"
)
CHAPTER_HEADING = re.compile(r"^# Chapter (\d+) · (.+)$", re.M)
SECTION_BREAK = re.compile(r"(?m)^={10,}[ \t]*$")
ZH_ANNOTATION = re.compile(r"^(译者待核实问题|原文缺失说明|原文修正说明)[：:]?\s*$")

BOOKS = {
    "lori": {
        "en": {
            "txt": "Daily_Words_The_Lords_Glory_with_Lori.txt",
            "epub": "Daily_Words_The_Lords_Glory_with_Lori.epub",
            "opf_source_from_url": True,
        },
        "zh": {
            "txt": "Daily_Words_The_Lords_Glory_with_Lori_zh.txt",
            "epub": "Daily_Words_The_Lords_Glory_with_Lori_zh.epub",
            "opf_source_from_url": False,
            "opf_source": "Daily_Words_The_Lords_Glory_with_Lori.txt",
        },
    },
    "dydi": {
        "en": {
            "txt": "DYDI_Messages_Declaring_Your_Destiny.txt",
            "epub": "DYDI_Messages_Declaring_Your_Destiny.epub",
            "opf_source_from_url": True,
        },
        "zh": {
            "txt": "DYDI_Messages_Declaring_Your_Destiny_zh.txt",
            "epub": "DYDI_Messages_Declaring_Your_Destiny_zh.epub",
            "opf_source_from_url": False,
            "opf_source": "DYDI_Messages_Declaring_Your_Destiny.txt",
        },
    },
}


@dataclass(frozen=True)
class LocaleProfile:
    language: str
    nav_title: str
    date_prefixes: tuple[str, ...]
    url_prefixes: tuple[str, ...]
    url_label: str
    source_label: str
    collected_label: str
    empty_body: str
    annotation: re.Pattern[str] | None
    use_zh_title: bool

    def cover_stats(self, count: int) -> str:
        if self.use_zh_title:
            return f"简体中文 · {count}篇"
        return f"English · {count} entries"


LOCALES = {
    "zh": LocaleProfile(
        language="zh-Hans",
        nav_title="目录",
        date_prefixes=("日期：", "日期:", "Date:"),
        url_prefixes=("原文：", "原文:", "URL:", "网址："),
        url_label="原文：",
        source_label="原文来源：",
        collected_label="原文采集时间：",
        empty_body="［无文字稿正文］",
        annotation=ZH_ANNOTATION,
        use_zh_title=True,
    ),
    "en": LocaleProfile(
        language="en",
        nav_title="Contents",
        date_prefixes=("Date:",),
        url_prefixes=("URL:",),
        url_label="URL: ",
        source_label="Source: ",
        collected_label="Collected: ",
        empty_body="[No transcript body]",
        annotation=None,
        use_zh_title=False,
    ),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def parse_header(text: str, locale: str) -> dict[str, str]:
    preamble = text.split("========================================================================", 1)[0]
    lines = [ln.strip() for ln in preamble.splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("# "):
        raise ValueError("missing book title")
    header: dict[str, str] = {"title": lines[0][2:].strip()}
    for line in lines[1:]:
        if "：" in line:
            key, value = line.split("：", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        header[key.strip()] = value.strip()
    if locale == "zh":
        header["creator"] = header.get("作者／事工", "")
        header["source_url"] = header.get("原文来源", "")
        header["collected"] = header.get("原文采集时间", "")
    else:
        header["creator"] = header.get("Author / Channel") or header.get("Author / Ministry", "")
        header["source_url"] = header.get("Source", "")
        header["collected"] = header.get("Collected", "")
    return header


def display_title(heading_line: str, profile: LocaleProfile) -> str:
    match = CHAPTER_HEADING.match(heading_line.strip())
    if not match:
        raise ValueError(f"unexpected chapter heading: {heading_line!r}")
    number, rest = match.groups()
    if profile.use_zh_title:
        return f"第 {number} 篇 · {rest}"
    return f"Chapter {number} · {rest}"


def annotation_start(text: str, profile: LocaleProfile) -> bool:
    if profile.annotation is None:
        return False
    line = text.split("\n", 1)[0].strip()
    return bool(profile.annotation.match(line))


def trim_annotation_block(paragraph: str, profile: LocaleProfile) -> str:
    kept: list[str] = []
    for line in paragraph.splitlines():
        if annotation_start(line, profile):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def meta_line_html(line: str, profile: LocaleProfile) -> str | None:
    for prefix in profile.date_prefixes:
        if line.startswith(prefix):
            return f'<p class="meta">{html.escape(line)}</p>'
    for prefix in profile.url_prefixes:
        if line.startswith(prefix):
            url = line[len(prefix) :].strip()
            safe = html.escape(url, quote=True)
            return (
                f'<p class="meta">{html.escape(profile.url_label)}'
                f'<a href="{safe}">{safe}</a></p>'
            )
    return None


def is_meta_line(line: str, profile: LocaleProfile) -> bool:
    return line.startswith(profile.date_prefixes) or line.startswith(profile.url_prefixes)


def chapter_body(section: str, profile: LocaleProfile) -> tuple[str, list[str]]:
    section = SECTION_BREAK.split(section, maxsplit=1)[0].strip()
    parts = paragraphs(section)
    if not parts:
        raise ValueError("empty chapter section")
    title = display_title(parts[0], profile)
    body: list[str] = []
    idx = 1
    while idx < len(parts) and is_meta_line(parts[idx], profile):
        idx += 1
    while idx < len(parts):
        if annotation_start(parts[idx], profile):
            break
        trimmed = trim_annotation_block(parts[idx], profile)
        if trimmed:
            body.append(trimmed)
        idx += 1
    if not body:
        body = [profile.empty_body]
    return title, body


def split_chapters(text: str) -> list[str]:
    sections = re.split(r"(?m)(?=^# Chapter \d+ · )", text)
    return [s for s in sections if s.startswith("# Chapter ") and SECTION_BREAK.split(s, 1)[0].strip()]


def xhtml_page(title: str, body: str, profile: LocaleProfile) -> str:
    safe_title = html.escape(title)
    lang = profile.language
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">'
        f"<head><meta charset=\"utf-8\"/><title>{safe_title}</title>"
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>'
        f"<body>{body}</body></html>"
    )


def build_chapter(
    section: str, index: int, profile: LocaleProfile
) -> tuple[str, str, str]:
    title, body_paras = chapter_body(section, profile)
    part_lines = paragraphs(SECTION_BREAK.split(section, 1)[0])
    meta_bits: list[str] = []
    for line in part_lines[1:]:
        if is_meta_line(line, profile):
            bit = meta_line_html(line, profile)
            if bit:
                meta_bits.append(bit)
        else:
            break
    content = [f"<h1>{html.escape(title)}</h1>", *meta_bits]
    for para in body_paras:
        content.append(f"<p>{html.escape(para)}</p>")
    href = f"chapter-{index:03d}.xhtml"
    return href, title, xhtml_page(title, "".join(content), profile)


def build_cover(header: dict[str, str], chapter_count: int, profile: LocaleProfile) -> str:
    title = header["title"]
    creator = header["creator"]
    source_url = html.escape(header["source_url"], quote=True)
    collected = html.escape(header["collected"])
    body = (
        '<div class="cover">'
        f"<h1>{html.escape(title)}</h1>"
        f"<p>{html.escape(creator)}</p>"
        f"<p>{html.escape(profile.cover_stats(chapter_count))}</p>"
        f'<p class="meta">{html.escape(profile.source_label)}'
        f'<a href="{source_url}">{source_url}</a></p>'
        f'<p class="meta">{html.escape(profile.collected_label)}{collected}</p>'
        "</div>"
    )
    return xhtml_page(title, body, profile)


def build_nav(titles: list[tuple[str, str]], profile: LocaleProfile) -> str:
    items = "".join(
        f'<li><a href="{html.escape(href, quote=True)}">{html.escape(title)}</a></li>'
        for href, title in titles
    )
    body = f'<h1>{html.escape(profile.nav_title)}</h1><nav epub:type="toc" id="toc"><ol>{items}</ol></nav>'
    return xhtml_page(profile.nav_title, body, profile)


def build_ncx(book_id: str, book_title: str, titles: list[tuple[str, str]]) -> str:
    points = []
    for order, (href, title) in enumerate(titles, start=1):
        points.append(
            f'<navPoint id="n{order}" playOrder="{order}">'
            f"<navLabel><text>{html.escape(title)}</text></navLabel>"
            f'<content src="{html.escape(href, quote=True)}"/>'
            "</navPoint>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        "<head>"
        f'<meta name="dtb:uid" content="{html.escape(book_id)}"/>'
        '<meta name="dtb:depth" content="1"/>'
        '<meta name="dtb:totalPageCount" content="0"/>'
        '<meta name="dtb:maxPageNumber" content="0"/>'
        "</head>"
        f"<docTitle><text>{html.escape(book_title)}</text></docTitle>"
        f"<navMap>{''.join(points)}</navMap></ncx>"
    )


def build_opf(
    book_id: str,
    header: dict[str, str],
    opf_source: str,
    profile: LocaleProfile,
    modified: str,
    manifest: list[tuple[str, str, str, str]],
    spine: list[str],
) -> str:
    manifest_xml = "".join(
        f'<item id="{item_id}" href="{href}" media-type="{media_type}"{props}/>'
        for item_id, href, media_type, props in manifest
    )
    spine_xml = "".join(f'<itemref idref="{item_id}"/>' for item_id in spine)
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="bookid">{html.escape(book_id)}</dc:identifier>'
        f"<dc:title>{html.escape(header['title'])}</dc:title>"
        f"<dc:creator>{html.escape(header['creator'])}</dc:creator>"
        f"<dc:language>{profile.language}</dc:language>"
        f"<dc:source>{html.escape(opf_source)}</dc:source>"
        f'<meta property="dcterms:modified">{modified}</meta>'
        "</metadata>"
        f"<manifest>{manifest_xml}</manifest>"
        f'<spine toc="ncx">{spine_xml}</spine>'
        "</package>"
    )


def write_epub(out_path: Path, payload: dict) -> None:
    with zipfile.ZipFile(out_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in payload.items():
            archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)


def opf_source(spec: dict, header: dict[str, str]) -> str:
    if spec.get("opf_source_from_url"):
        return header["source_url"]
    return spec["opf_source"]


def build_book(book_key: str, locale: str) -> Path:
    spec = BOOKS[book_key][locale]
    profile = LOCALES[locale]
    txt_path = ROOT / spec["txt"]
    out_path = ROOT / spec["epub"]
    text = read_text(txt_path)
    header = parse_header(text, locale)
    sections = split_chapters(text)
    chapter_pages: list[tuple[str, str, str]] = []
    toc_entries: list[tuple[str, str]] = []
    for index, section in enumerate(sections, start=1):
        href, title, page = build_chapter(section, index, profile)
        chapter_pages.append((href, title, page))
        toc_entries.append((href, title))
    modified = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    book_id = "urn:sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    manifest: list[tuple[str, str, str, str]] = [
        ("css", "style.css", "text/css", ""),
        ("nav", "nav.xhtml", "application/xhtml+xml", ' properties="nav"'),
        ("ncx", "toc.ncx", "application/x-dtbncx+xml", ""),
        ("cover", "cover.xhtml", "application/xhtml+xml", ""),
    ]
    for idx, (href, _title, _page) in enumerate(chapter_pages):
        manifest.append((f"c{idx}", href, "application/xhtml+xml", ""))
    spine = ["cover", "nav", *[item[0] for item in manifest[4:]]]
    payload = {
        "META-INF/container.xml": (
            '<?xml version="1.0"?>'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>'
        ),
        "OEBPS/style.css": STYLE,
        "OEBPS/cover.xhtml": build_cover(header, len(chapter_pages), profile),
        "OEBPS/nav.xhtml": build_nav(toc_entries, profile),
        "OEBPS/toc.ncx": build_ncx(book_id, header["title"], toc_entries),
        "OEBPS/content.opf": build_opf(
            book_id,
            header,
            opf_source(spec, header),
            profile,
            modified,
            manifest,
            spine,
        ),
    }
    for href, _title, page in chapter_pages:
        payload[f"OEBPS/{href}"] = page
    write_epub(out_path, payload)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lang",
        choices=["zh", "en", "all"],
        default="all",
        help="language edition to build (default: all)",
    )
    parser.add_argument("books", nargs="*", choices=sorted(BOOKS), help="book keys (default: all)")
    args = parser.parse_args()
    targets = args.books or sorted(BOOKS)
    locales = ["zh", "en"] if args.lang == "all" else [args.lang]
    for book in targets:
        for locale in locales:
            out = build_book(book, locale)
            print(f"Wrote {out}")


if __name__ == "__main__":
    main()