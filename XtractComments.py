#!/usr/bin/env python3
import argparse
import os
import sys

import fitz  # PyMuPDF

CM_TO_PT = 72.0 / 2.54  # points per cm


def sanitize_quotes(text: str) -> str:
    """Replace double quotes with single quotes and trim whitespace."""
    if text is None:
        return ""
    return text.replace('"', "'").strip()


def with_ellipsis(text: str) -> str:
    """Wrap the highlighted text with ellipsis, if not empty."""
    t = text.strip()
    if not t:
        return t
    return f'"...{t}..."'


# -------------------------------------------------------------------------
# 1) PRIMARY: detect printed line numbers in the margin
# -------------------------------------------------------------------------

def get_page_line_numbers(page, header_margin_cm=1.5, margin_frac=0.15):
    """
    Detect printed line numbers on a page.

    Heuristic:
      - Use page.get_text("words").
      - Consider only numeric words (all digits).
      - Only in the left margin: x1 <= x0 + margin_frac * page_width.
      - Ignore numbers too close to the top (header_margin_cm).

    Returns:
        A list of dicts:
            [{"line_number": int, "y_center": float}, ...]
        sorted by y_center (top to bottom).
        If empty, there are no detectable printed line numbers on this page.
    """
    words = page.get_text("words")
    # words: (x0, y0, x1, y1, "word", block_no, line_no, word_no)

    page_rect = page.rect
    page_width = page_rect.width

    # Left margin cutoff
    margin_x = page_rect.x0 + margin_frac * page_width

    # Header cutoff (ignore page numbers / running headers near top)
    header_margin_pts = header_margin_cm * CM_TO_PT
    header_cutoff_y = page_rect.y0 + header_margin_pts

    line_candidates = []

    for w in words:
        if len(w) < 5:
            continue
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]

        # Only consider words in the left margin, below header cutoff
        if x1 > margin_x:
            continue
        if y0 < header_cutoff_y:
            continue

        txt = text.strip()
        if not txt.isdigit():
            continue

        try:
            ln = int(txt)
        except ValueError:
            continue

        y_center = (y0 + y1) / 2.0
        line_candidates.append((ln, y_center))

    if not line_candidates:
        return []

    # There may be duplicates for the same number; average their positions
    by_number = {}
    for ln, yc in line_candidates:
        by_number.setdefault(ln, []).append(yc)

    result = []
    for ln, ylist in by_number.items():
        avg_y = sum(ylist) / len(ylist)
        result.append({"line_number": ln, "y_center": avg_y})

    # Sort top to bottom
    result.sort(key=lambda d: d["y_center"])
    return result


def get_line_number_for_annotation_from_margin(annot, line_numbers):
    """
    Given an annotation and a list of detected printed line numbers
    (with their vertical centers), choose the printed line number whose
    y_center is closest to the annotation's vertical center.

    Returns:
        int or None
    """
    if not line_numbers:
        return None

    rect = annot.rect
    y_center = (rect.y0 + rect.y1) / 2.0

    best_ln = None
    best_dist = None

    for ln in line_numbers:
        dist = abs(y_center - ln["y_center"])
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_ln = ln["line_number"]

    return best_ln


# -------------------------------------------------------------------------
# 2) FALLBACK: approximate line index when no printed numbers exist
# -------------------------------------------------------------------------

def get_page_body_lines(page, header_margin_cm=1.5):
    """
    Build a list of logical 'body' text lines on the page using page.get_text('dict'),
    ignoring lines located within `header_margin_cm` from the top of the page.

    This is the fallback when no printed line numbers are present.

    Returns:
        lines: list of dicts:
            - index: 1-based body line index (starting after header region)
            - rect:  fitz.Rect of the line
            - text:  string of the line
    """
    text_dict = page.get_text("dict")
    raw_lines = []

    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            line_bbox = line.get("bbox", None)
            spans = line.get("spans", [])

            # Join spans as one visual line
            line_text_parts = [span.get("text", "") for span in spans]
            line_text = "".join(line_text_parts).strip()
            if not line_text:
                continue

            # If bbox missing, compute from spans
            if line_bbox is None and spans:
                xs0, ys0, xs1, ys1 = [], [], [], []
                for sp in spans:
                    sb = sp.get("bbox", None)
                    if sb is None:
                        continue
                    x0, y0, x1, y1 = sb
                    xs0.append(x0)
                    ys0.append(y0)
                    xs1.append(x1)
                    ys1.append(y1)
                if xs0 and ys0 and xs1 and ys1:
                    line_bbox = (min(xs0), min(ys0), max(xs1), max(ys1))

            if line_bbox is None:
                continue

            x0, y0, x1, y1 = line_bbox
            rect = fitz.Rect(x0, y0, x1, y1)
            raw_lines.append({"rect": rect, "text": line_text, "y0": y0, "x0": x0})

    # Sort by vertical then horizontal position
    raw_lines.sort(key=lambda d: (d["y0"], d["x0"]))

    # Header cutoff
    page_top = page.rect.y0
    header_margin_pts = header_margin_cm * CM_TO_PT
    header_cutoff_y = page_top + header_margin_pts

    # Keep only body lines
    body_candidates = [d for d in raw_lines if d["rect"].y0 >= header_cutoff_y]

    lines = []
    for i, entry in enumerate(body_candidates, start=1):
        lines.append(
            {
                "index": i,          # 1-based line index in body
                "rect": entry["rect"],
                "text": entry["text"],
            }
        )

    return lines


def get_fallback_line_index_for_annotation(annot, page_lines):
    """
    Fallback line index when no printed line numbers exist:
    - Use the annotation's vertical center.
    - Pick the body line whose vertical band is closest to that center.
    """
    if not page_lines:
        return None

    rect = annot.rect
    y_center = (rect.y0 + rect.y1) / 2.0

    best_line_index = None
    best_dist = None

    for line in page_lines:
        ly0 = line["rect"].y0
        ly1 = line["rect"].y1

        if ly0 <= y_center <= ly1:
            return line["index"]

        dist = min(abs(y_center - ly0), abs(y_center - ly1))
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_line_index = line["index"]

    return best_line_index


# -------------------------------------------------------------------------
# 3) Annotation text extraction
# -------------------------------------------------------------------------

def extract_highlight_text(page, annot):
    """
    Extract the text covered by a (highlight/underline/squiggly/strikeout) annotation,
    using the annotation rectangle as clipping region.
    """
    rect = annot.rect
    return page.get_text("text", clip=rect).strip()


# -------------------------------------------------------------------------
# 4) Main extraction logic with primary + fallback
# -------------------------------------------------------------------------

def extract_annotations_to_txt(
    pdf_path,
    output_txt,
    header_margin_cm=1.5,
    margin_frac=0.15,
):
    """
    Extract annotations from a PDF and write them to a TXT file.

    Output:
      Comments to the Author

      Page <x>, line <y>, ...<highlighted text>...: <comment>
      Page <x>, line <y>: substitute "...<highlighted text>..." for "<comment>"

    Line resolution:
      - First try to use printed line numbers detected in the margin.
      - If no printed line numbers are found for a page, fall back to
        approximated body-line indices based on text layout.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(pdf_path)

    lines_out = []
    lines_out.append("Comments to the Author")
    lines_out.append("")  # blank line

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1

        # 1) Try to detect printed line numbers for this page
        line_numbers = get_page_line_numbers(
            page,
            header_margin_cm=header_margin_cm,
            margin_frac=margin_frac,
        )

        # 2) Prepare fallback body lines only if needed
        body_lines = None
        use_margin_numbers = bool(line_numbers)

        if not use_margin_numbers:
            body_lines = get_page_body_lines(page, header_margin_cm=header_margin_cm)

        annot = page.first_annot
        while annot:
            annot_type_code, annot_type_name = annot.type
            annot_type = annot_type_name.lower()

            # We handle text-markup annotations only
            if annot_type in ("highlight", "underline", "squiggly", "strikeout"):
                # Extract highlighted text
                try:
                    highlighted_text = extract_highlight_text(page, annot)
                except Exception as e:
                    highlighted_text = f"[ERROR extracting text: {e}]"

                # ---- NEW: remove newlines completely ----
                highlighted_text = highlighted_text.replace("\r", " ").replace("\n", " ")
                highlighted_text = " ".join(highlighted_text.split())   # collapse multiple spaces
                # -----------------------------------------

                highlighted_text = sanitize_quotes(highlighted_text)
                highlighted_display = with_ellipsis(highlighted_text)

                # Annotation comment
                info = annot.info or {}
                comment = info.get("content", "") or ""
                comment = sanitize_quotes(comment)

                # Decide line number:
                if use_margin_numbers:
                    line_number = get_line_number_for_annotation_from_margin(
                        annot, line_numbers
                    )
                else:
                    line_number = get_fallback_line_index_for_annotation(
                        annot, body_lines
                    )

                line_display = line_number if line_number is not None else ""

                # Formatting
                if annot_type == "strikeout":
                    # Crossed text
                    if comment:
                        entry = (
                            f'Page {page_number}, line {line_display}: substitute '
                            f'{highlighted_display} for "{comment}"'
                        )
                    else:
                        entry = (
                            f'Page {page_number}, line {line_display}: strike out '
                            f'{highlighted_display}'
                        )
                else:
                    # Highlight / underline / squiggly
                    entry = (
                        f"Page {page_number}, line {line_display}, "
                        f"{highlighted_display}: {comment}"
                    )

                lines_out.append(entry)

            annot = annot.next

    # Write TXT file
    with open(output_txt, "w", encoding="utf-8") as f:
        for line in lines_out:
            f.write(line + "\n")


# -------------------------------------------------------------------------
# 5) CLI
# -------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract PDF annotations to TXT.\n"
            "Primary: use printed line numbers from the margin.\n"
            "Fallback: approximate line indices when no numbers are present.\n"
            'Output format:\n'
            '  Page <x>, line <y>, ...<highlighted text>...: <comment>\n'
            '  Page <x>, line <y>: substitute "...<highlighted text>..." for "<comment>"'
        )
    )
    parser.add_argument("pdf", help="Path to the PDF file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output TXT file (default: <pdf_basename>_annotations.txt).",
        default=None,
    )
    parser.add_argument(
        "--header-margin-cm",
        type=float,
        default=1.5,
        help="Ignore line numbers / body text above this distance from the top (default: 1.5 cm).",
    )
    parser.add_argument(
        "--margin-frac",
        type=float,
        default=0.15,
        help="Fraction of page width treated as left margin for printed line numbers (default: 0.15).",
    )

    args = parser.parse_args()
    pdf_path = args.pdf

    if args.output:
        output_txt = args.output
    else:
        base, _ = os.path.splitext(pdf_path)
        output_txt = base + "_annotations.txt"

    try:
        extract_annotations_to_txt(
            pdf_path,
            output_txt,
            header_margin_cm=args.header_margin_cm,
            margin_frac=args.margin_frac,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Annotations extracted to: {output_txt}")


if __name__ == "__main__":
    main()
