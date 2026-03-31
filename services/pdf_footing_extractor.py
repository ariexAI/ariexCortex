"""
pdf_footing_extractor.py
Extract text from scanned PDFs via OCR and parse footing dimensions.
"""

from __future__ import annotations

import re
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    page_number: int
    text: str
    footing_sizes: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    pdf_path: str
    pages: list[PageResult] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(
            f"--- Page {p.page_number} ---\n{p.text}" for p in self.pages
        )

    @property
    def all_footing_sizes(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for page in self.pages:
            for size in page.footing_sizes:
                normalised = _normalise_dimension(size)
                if normalised not in seen:
                    seen.add(normalised)
                    result.append(normalised)
        return result


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def extract_text_from_pdf(
    pdf_path: str | Path,
    poppler_path: Optional[str] = None,
    dpi: int = 300,
    lang: str = "eng",
    tesseract_config: str = "--psm 6",
) -> ExtractionResult:
    """
    Convert every page of *pdf_path* to an image and run Tesseract OCR on it.

    Args:
        pdf_path:        Path to the PDF file.
        poppler_path:    Path to the Poppler ``bin`` directory (Windows only).
                         Leave as ``None`` on Linux/macOS where Poppler is on PATH.
        dpi:             Render resolution – higher = better accuracy, slower.
        lang:            Tesseract language pack(s), e.g. ``"eng"`` or ``"eng+fra"``.
        tesseract_config: Extra Tesseract flags.

    Returns:
        ExtractionResult with per-page text and discovered footing sizes.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    log.info("Converting '%s' to images at %d DPI …", pdf_path.name, dpi)

    convert_kwargs: dict = {
    "dpi": dpi,
    "poppler_path": r"C:\poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin"
}

    images: list[Image.Image] = convert_from_path(str(pdf_path), **convert_kwargs)
    log.info("PDF has %d page(s).", len(images))

    result = ExtractionResult(pdf_path=str(pdf_path))

    for i, image in enumerate(images, start=1):
        log.info("  OCR – page %d / %d …", i, len(images))
        text = pytesseract.image_to_string(image, lang=lang, config=tesseract_config)
        footings = find_footing_sizes(text)
        result.pages.append(PageResult(page_number=i, text=text, footing_sizes=footings))

    return result


# ---------------------------------------------------------------------------
# Footing-size extraction
# ---------------------------------------------------------------------------

# Matches patterns such as:
#   1.5 x 1.5        1500 x 1500       2.4X3.0
#   1.5x1.5m         1500×1500 mm      3' x 3'
#   1500 x 1500 x 500  (3-D footings)
_DIMENSION_PATTERN = re.compile(
    r"""
    (?<!\w)                          # not preceded by a word char
    (
        \d+(?:\.\d+)?                # first number  (int or float)
        \s*[xX×]\s*                  # separator: x / X / ×
        \d+(?:\.\d+)?                # second number
        (?:                          # optional third dimension
            \s*[xX×]\s*
            \d+(?:\.\d+)?
        )?
        (?:\s*(?:mm|cm|m|ft|'))?     # optional unit
    )
    (?!\w)                           # not followed by a word char
    """,
    re.VERBOSE,
)

# Noise filter: skip obvious non-footing hits like "1x1" (too small) or "page 2x3"
_MIN_VALUE = 0.1   # anything below this in any dimension is likely noise
_MAX_VALUE = 50_000  # sanity upper bound (mm)


def _parse_numbers(raw: str) -> list[float]:
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", raw)]


def _is_plausible_footing(raw: str) -> bool:
    nums = _parse_numbers(raw)
    return all(_MIN_VALUE <= n <= _MAX_VALUE for n in nums)


def _normalise_dimension(raw: str) -> str:
    """Return a tidy 'N x M' (or 'N x M x P') string."""
    nums = _parse_numbers(raw)
    unit_match = re.search(r"(mm|cm|m|ft|')\s*$", raw.strip(), re.IGNORECASE)
    unit = f" {unit_match.group(1)}" if unit_match else ""
    return " x ".join(str(int(n) if n == int(n) else n) for n in nums) + unit


def find_footing_sizes(text: str) -> list[str]:
    """
    Return a deduplicated list of plausible footing dimension strings found in *text*.
    """
    raw_matches = _DIMENSION_PATTERN.findall(text)
    seen: set[str] = set()
    results: list[str] = []
    for raw in raw_matches:
        if not _is_plausible_footing(raw):
            continue
        normalised = _normalise_dimension(raw)
        if normalised not in seen:
            seen.add(normalised)
            results.append(normalised)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract footing sizes from a scanned structural PDF."
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--poppler", default=None, help="Path to Poppler bin (Windows)")
    parser.add_argument("--dpi", type=int, default=300, help="Render DPI (default 300)")
    parser.add_argument("--lang", default="eng", help="Tesseract language (default eng)")
    parser.add_argument("--dump-text", action="store_true", help="Print full OCR text")
    args = parser.parse_args()

    try:
        result = extract_text_from_pdf(
            args.pdf,
            poppler_path=args.poppler,
            dpi=args.dpi,
            lang=args.lang,
        )
    except FileNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    if args.dump_text:
        print("\n===== OCR TEXT =====")
        print(result.full_text)

    print("\n===== FOOTING SIZES FOUND =====")
    sizes = result.all_footing_sizes
    if sizes:
        for size in sizes:
            print(f"  {size}")
    else:
        print("  (none detected)")

    print("\n===== PER-PAGE SUMMARY =====")
    for page in result.pages:
        print(f"  Page {page.page_number}: {page.footing_sizes or '—'}")


if __name__ == "__main__":
    main()
