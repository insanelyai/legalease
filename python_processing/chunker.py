"""
Indian Legal PDF Chunker — Production Grade
============================================
Handles: Acts, Bills, Gazette Notifications
Output:  Vector-DB-ready JSON with rich legal metadata

Strategy:
- Section-boundary chunking (not word-window)
- Proviso + Explanation attached to parent section
- Cross-reference extraction
- Parent-child chunk linking for hybrid retrieval
- Scanned PDF fallback via OCR

Usage:
    python chunker.py --input ./pdfs --output ./chunks.json
    python chunker.py --input ./pdfs --output ./chunks.json --ocr   # for scanned PDFs
"""

import re
import json
import uuid
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import pdfplumber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────

@dataclass
class LegalChunk:
    id: str
    text: str
    chunk_type: str          # preamble | definition | section | schedule | amendment
    # child chunks point to their parent section chunk
    parent_id: Optional[str]

    # Legal location
    act_name: str
    act_year: Optional[int]
    law_type: str

    chapter_num: Optional[str]
    chapter_title: Optional[str]
    section_num: Optional[str]
    section_title: Optional[str]

    # Content flags
    has_proviso: bool
    has_explanation: bool
    is_definition_section: bool
    cross_refs: list[str]

    # Source
    source_file: str
    page_range: list[int]
    chunk_index: int
    word_count: int


# ─────────────────────────────────────────────
# REGEX PATTERNS (tuned for Indian acts)
# ─────────────────────────────────────────────

# Chapter headings: "CHAPTER I", "CHAPTER III", "PART A"
RE_CHAPTER = re.compile(
    r'(?:^|\n)\s*(CHAPTER\s+[IVXLCDM\d]+|PART\s+[A-Z\d]+)',
    re.MULTILINE
)

# Section headings — Indian acts: "35. Title of section.-" or "35. Title.—"
# Title starts with uppercase, followed by a separator (.- or .— or .-)
RE_SECTION = re.compile(
    r'(?:^|\n)\s*(\d+[A-Z]?)\.\s+([A-Z][^.\n]{3,80})[.\-\u2014]',
    re.MULTILINE
)

# Sub-section: "(1)", "(2)", "(a)", "(i)"
RE_SUBSECTION = re.compile(
    r'^\s*\((\d+|[a-z]|i{1,3}v?|vi{0,3})\)\s+', re.MULTILINE)

# Proviso lines
RE_PROVISO = re.compile(r'\bProvided\s+(?:further\s+)?that\b', re.IGNORECASE)

# Explanation blocks
RE_EXPLANATION = re.compile(r'\bExplanation\s*[\.\-—:]\s*', re.IGNORECASE)

# Cross-references: "section 35", "sub-section (3) of section 12", "clause (a)"
RE_CROSS_REF = re.compile(
    r'\b(?:section|sub-section|clause|article|schedule|rule|order)\s+'
    r'(?:\(\d+\)\s+of\s+section\s+)?\d+[A-Z]?(?:\s*\(\d+\))?(?:\s*\([a-z]\))?',
    re.IGNORECASE
)

# Definition sections
RE_IS_DEFINITION = re.compile(r'\bdefin(?:ition|e|es|itions)\b', re.IGNORECASE)

# Year from act name
RE_YEAR = re.compile(r'\b(19|20)\d{2}\b')


# ─────────────────────────────────────────────
# ACT METADATA INFERENCE
# ─────────────────────────────────────────────

LAW_TYPE_KEYWORDS = {
    "consumer_protection": ["consumer", "copra", "defect", "unfair trade"],
    "labour_law":          ["labour", "labor", "industrial", "employment", "workmen", "wages", "factory"],
    "family_law":          ["marriage", "divorce", "matrimonial", "hindu", "muslim personal", "guardian", "adoption"],
    "criminal":            ["penal", "ipc", "crpc", "criminal procedure", "evidence", "punishment"],
    "constitutional":      ["constitution", "fundamental rights", "directive principles"],
    "property":            ["transfer of property", "registration", "stamp", "land acquisition"],
    "company":             ["companies act", "sebi", "insolvency", "bankruptcy"],
    "tax":                 ["income tax", "gst", "customs", "excise"],
    "data_privacy":        ["data protection", "personal data", "privacy"],
}


def infer_law_type(filename: str, first_page_text: str = "") -> str:
    combined = (filename + " " + first_page_text[:500]).lower()
    for law_type, keywords in LAW_TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return law_type
    return "general"


def infer_act_name(filename: str, first_page_text: str = "") -> tuple[str, Optional[int]]:
    """Try to extract the Act's proper name and year from first page text."""
    # Look for common pattern: "THE XYZ ACT, YYYY"
    match = re.search(
        r'THE\s+([A-Z][A-Z\s,\(\)]+?ACT(?:URE|ION)?),?\s*(\d{4})', first_page_text[:800])
    if match:
        name = match.group(0).strip()
        year = int(match.group(2))
        return name, year

    # Fallback: clean up filename
    stem = Path(filename).stem
    cleaned = re.sub(r'[_\-]+', ' ', stem).title()
    year_match = RE_YEAR.search(stem)
    year = int(year_match.group(0)) if year_match else None
    return cleaned, year


# ─────────────────────────────────────────────
# PDF TEXT EXTRACTION
# ─────────────────────────────────────────────

def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text per page using pdfplumber. Returns [{page_num, text}]."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text and text.strip():
                pages.append({
                    "page_num": i + 1,
                    "text": text.strip()
                })
    return pages


def extract_pages_ocr(pdf_path: str) -> list[dict]:
    """OCR fallback for scanned PDFs. Requires pytesseract + pdf2image."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError(
            "Install: pip install pytesseract pdf2image && apt install tesseract-ocr poppler-utils")

    log.info(f"Running OCR on {pdf_path} (this may take a while)...")
    pages_img = convert_from_path(pdf_path, dpi=300)
    pages = []
    for i, img in enumerate(pages_img):
        text = pytesseract.image_to_string(img, lang="eng")
        if text.strip():
            pages.append({"page_num": i + 1, "text": text.strip()})
    return pages


def is_scanned(pdf_path: str) -> bool:
    """Quick heuristic: if first page has <30 chars of text, likely scanned."""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return True
        text = pdf.pages[0].extract_text() or ""
        return len(text.strip()) < 30


# ─────────────────────────────────────────────
# TEXT CLEANING
# ─────────────────────────────────────────────

def clean_legal_text(text: str) -> str:
    """Remove PDF extraction artifacts common in Indian legal docs."""
    # Remove running headers/footers (repeated short lines)
    lines = text.split('\n')
    line_freq: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if 5 < len(stripped) < 80:
            line_freq[stripped] = line_freq.get(stripped, 0) + 1

    # Lines appearing 3+ times are likely headers/footers
    boilerplate = {k for k, v in line_freq.items() if v >= 3}
    lines = [l for l in lines if l.strip() not in boilerplate]
    text = '\n'.join(lines)

    # Collapse excess whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # Remove lone page numbers
    text = re.sub(r'(?m)^\s*\d{1,4}\s*$', '', text)

    # Fix broken hyphenation across lines
    text = re.sub(r'-\n(\w)', r'\1', text)

    return text.strip()


# ─────────────────────────────────────────────
# SECTION SPLITTER
# ─────────────────────────────────────────────

@dataclass
class RawSection:
    section_num: Optional[str]
    section_title: Optional[str]
    text: str
    start_page: int
    end_page: int
    chapter_num: Optional[str] = None
    chapter_title: Optional[str] = None


def split_into_sections(pages: list[dict]) -> list[RawSection]:
    """
    Split document into sections using boundary detection.
    Tracks chapter context as we go.
    """
    # Build a flat list of (page_num, line) pairs
    all_lines: list[tuple[int, str]] = []
    for page in pages:
        for line in page["text"].split('\n'):
            all_lines.append((page["page_num"], line))

    sections: list[RawSection] = []
    current_chapter_num: Optional[str] = None
    current_chapter_title: Optional[str] = None

    # Preamble section
    preamble_lines: list[str] = []
    preamble_pages: list[int] = []

    current_section: Optional[RawSection] = None
    current_lines: list[str] = []
    current_pages: list[int] = []

    def flush_section():
        nonlocal current_section, current_lines, current_pages
        if current_section and current_lines:
            current_section.text = '\n'.join(current_lines).strip()
            current_section.start_page = current_pages[0] if current_pages else 0
            current_section.end_page = current_pages[-1] if current_pages else 0
            current_section.chapter_num = current_chapter_num
            current_section.chapter_title = current_chapter_title
            sections.append(current_section)
        current_section = None
        current_lines = []
        current_pages = []

    in_preamble = True

    for page_num, line in all_lines:
        stripped = line.strip()

        # ── Chapter detection ──
        ch_match = RE_CHAPTER.search('\n' + line)
        if ch_match and len(stripped) < 60:  # chapter headings are short lines
            flush_section()
            in_preamble = False
            current_chapter_num = ch_match.group(1).strip()
            current_chapter_title = None
            current_lines = [line]
            current_pages = [page_num]
            continue

        # ── Section detection ──
        sec_match = RE_SECTION.search('\n' + line)
        if sec_match:
            flush_section()
            in_preamble = False
            sec_num = sec_match.group(1)
            sec_title_raw = (sec_match.group(2) or "").strip().rstrip('.')
            current_section = RawSection(
                section_num=sec_num,
                section_title=sec_title_raw or None,
                text="",
                start_page=page_num,
                end_page=page_num
            )
            current_lines = [line]
            current_pages = [page_num]
            continue

        # ── Accumulate lines ──
        if in_preamble:
            preamble_lines.append(line)
            preamble_pages.append(page_num)
        else:
            current_lines.append(line)
            current_pages.append(page_num)

    flush_section()

    # Prepend preamble as its own pseudo-section
    if preamble_lines:
        preamble_text = '\n'.join(preamble_lines).strip()
        if len(preamble_text) > 50:
            sections.insert(0, RawSection(
                section_num=None,
                section_title="Preamble",
                text=preamble_text,
                start_page=preamble_pages[0] if preamble_pages else 1,
                end_page=preamble_pages[-1] if preamble_pages else 1
            ))

    return sections


# ─────────────────────────────────────────────
# CHUNK BUILDER
# ─────────────────────────────────────────────

MAX_CHUNK_WORDS = 1200   # upper limit before forced split
MIN_CHUNK_WORDS = 40     # ignore tiny fragments


def extract_cross_refs(text: str) -> list[str]:
    refs = RE_CROSS_REF.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for r in refs:
        r_clean = r.strip().lower()
        if r_clean not in seen:
            seen.add(r_clean)
            unique.append(r.strip())
    return unique


def word_count(text: str) -> int:
    return len(text.split())


def split_large_section(section: RawSection) -> list[RawSection]:
    """
    If a section exceeds MAX_CHUNK_WORDS, split at sub-section boundaries.
    Returns list of RawSection objects (first keeps section identity, rest are children).
    """
    text = section.text
    if word_count(text) <= MAX_CHUNK_WORDS:
        return [section]

    # Split at sub-section markers
    parts = RE_SUBSECTION.split(text)
    if len(parts) <= 1:
        # No sub-sections found, do a dumb word split with overlap
        words = text.split()
        chunks = []
        step = MAX_CHUNK_WORDS - 100
        for i in range(0, len(words), step):
            chunk_text = ' '.join(words[i:i+MAX_CHUNK_WORDS])
            sub = RawSection(
                section_num=section.section_num,
                section_title=section.section_title,
                text=chunk_text,
                start_page=section.start_page,
                end_page=section.end_page,
                chapter_num=section.chapter_num,
                chapter_title=section.chapter_title
            )
            chunks.append(sub)
        return chunks

    # Rebuild sub-sections
    sub_sections = []
    # parts alternates: text_before_first_match, marker1, text1, marker2, text2, ...
    # Actually re.split with a group gives: [pre, m1, t1, m2, t2, ...]
    i = 0
    current_sub = parts[0] if parts else ""
    while i < len(parts):
        block = parts[i]
        if word_count(current_sub + "\n" + block) > MAX_CHUNK_WORDS and current_sub.strip():
            sub = RawSection(
                section_num=section.section_num,
                section_title=section.section_title,
                text=current_sub.strip(),
                start_page=section.start_page,
                end_page=section.end_page,
                chapter_num=section.chapter_num,
                chapter_title=section.chapter_title
            )
            sub_sections.append(sub)
            current_sub = block
        else:
            current_sub += "\n" + block
        i += 1
    if current_sub.strip():
        sub = RawSection(
            section_num=section.section_num,
            section_title=section.section_title,
            text=current_sub.strip(),
            start_page=section.start_page,
            end_page=section.end_page,
            chapter_num=section.chapter_num,
            chapter_title=section.chapter_title
        )
        sub_sections.append(sub)
    return sub_sections


def infer_chunk_type(section: RawSection) -> str:
    if section.section_title and "preamble" in section.section_title.lower():
        return "preamble"
    if section.section_title and RE_IS_DEFINITION.search(section.section_title):
        return "definition"
    if section.section_num is None:
        return "preamble"
    # Schedule detection
    if re.search(r'\bSCHEDULE\b', section.text[:200], re.IGNORECASE):
        return "schedule"
    return "section"


def build_chunks(
    sections: list[RawSection],
    act_name: str,
    act_year: Optional[int],
    law_type: str,
    source_file: str
) -> list[LegalChunk]:
    chunks: list[LegalChunk] = []
    chunk_index = 0

    for section in sections:
        if word_count(section.text) < MIN_CHUNK_WORDS:
            continue

        sub_sections = split_large_section(section)
        parent_id = str(uuid.uuid4()) if len(sub_sections) > 1 else None

        for si, sub in enumerate(sub_sections):
            chunk_id = parent_id if (
                si == 0 and parent_id) else str(uuid.uuid4())
            is_child = si > 0 and parent_id is not None

            chunk = LegalChunk(
                id=chunk_id,
                text=sub.text,
                chunk_type=infer_chunk_type(section),
                parent_id=parent_id if is_child else None,
                act_name=act_name,
                act_year=act_year,
                law_type=law_type,
                chapter_num=sub.chapter_num,
                chapter_title=sub.chapter_title,
                section_num=sub.section_num,
                section_title=sub.section_title,
                has_proviso=bool(RE_PROVISO.search(sub.text)),
                has_explanation=bool(RE_EXPLANATION.search(sub.text)),
                is_definition_section=bool(
                    RE_IS_DEFINITION.search(sub.section_title or "")),
                cross_refs=extract_cross_refs(sub.text),
                source_file=source_file,
                page_range=[sub.start_page, sub.end_page],
                chunk_index=chunk_index,
                word_count=word_count(sub.text)
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks


# ─────────────────────────────────────────────
# PIPELINE ENTRY POINT
# ─────────────────────────────────────────────

def process_pdf(pdf_path: Path, use_ocr: bool = False) -> list[LegalChunk]:
    log.info(f"Processing: {pdf_path.name}")

    # 1. Extract text
    if use_ocr or is_scanned(str(pdf_path)):
        log.info(f"  → Scanned PDF detected, using OCR")
        pages = extract_pages_ocr(str(pdf_path))
    else:
        pages = extract_pages(str(pdf_path))

    if not pages:
        log.warning(f"  → No text extracted from {pdf_path.name}, skipping")
        return []

    # 2. Clean
    for page in pages:
        page["text"] = clean_legal_text(page["text"])

    # 3. Infer act metadata from first page
    first_text = pages[0]["text"] if pages else ""
    act_name, act_year = infer_act_name(pdf_path.name, first_text)
    law_type = infer_law_type(pdf_path.name, first_text)
    log.info(f"  → Act: {act_name} ({act_year}) | Type: {law_type}")

    # 4. Split into sections
    sections = split_into_sections(pages)
    log.info(f"  → Found {len(sections)} sections")

    # 5. Build chunks
    chunks = build_chunks(sections, act_name, act_year,
                          law_type, pdf_path.name)
    log.info(f"  → Generated {len(chunks)} chunks")

    return chunks


def process_directory(
    input_dir: str,
    output_file: str,
    use_ocr: bool = False,
    pretty: bool = True
):
    pdf_files = list(Path(input_dir).glob("*.pdf"))
    if not pdf_files:
        log.error(f"No PDFs found in {input_dir}")
        return

    log.info(f"Found {len(pdf_files)} PDF(s) to process")
    all_chunks: list[dict] = []

    for pdf_path in pdf_files:
        try:
            chunks = process_pdf(pdf_path, use_ocr=use_ocr)
            all_chunks.extend([asdict(c) for c in chunks])
        except Exception as e:
            log.error(f"Failed on {pdf_path.name}: {e}", exc_info=True)

    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False,
                  indent=2 if pretty else None)

    log.info(f"\n✓ Done. {len(all_chunks)} total chunks → {output_file}")

    # Print summary stats
    from collections import Counter
    law_types = Counter(c["law_type"] for c in all_chunks)
    chunk_types = Counter(c["chunk_type"] for c in all_chunks)
    with_proviso = sum(1 for c in all_chunks if c["has_proviso"])
    with_xrefs = sum(1 for c in all_chunks if c["cross_refs"])

    print("\n── Summary ──────────────────────────────")
    print(f"  Total chunks      : {len(all_chunks)}")
    print(f"  Law types         : {dict(law_types)}")
    print(f"  Chunk types       : {dict(chunk_types)}")
    print(f"  Has proviso       : {with_proviso}")
    print(f"  Has cross-refs    : {with_xrefs}")
    print("─────────────────────────────────────────")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Indian Legal PDF → Vector DB JSON Chunker")
    parser.add_argument("--input",  "-i", default="./pdfs",
                        help="Directory with PDF files")
    parser.add_argument(
        "--output", "-o", default="./chunks.json", help="Output JSON file path")
    parser.add_argument("--ocr",          action="store_true",
                        help="Force OCR for all PDFs")
    parser.add_argument("--compact",      action="store_true",
                        help="Compact JSON (no indent)")
    args = parser.parse_args()

    process_directory(
        input_dir=args.input,
        output_file=args.output,
        use_ocr=args.ocr,
        pretty=not args.compact
    )
