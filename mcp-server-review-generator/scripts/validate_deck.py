"""Structural self-checks for a generated .pptx, run automatically at the
end of build_deck.py. There is no automated visual QA (no LibreOffice/pdftoppm
rendering) -- these checks catch the failure
modes a bug in this generator could plausibly introduce (malformed XML,
dangling relationships, leftover placeholder text), not layout/overflow
issues. Manual visual review in PowerPoint/Keynote is still required.
"""

import re
import sys
import xml.dom.minidom as minidom
import zipfile
from pathlib import Path

import common

PLACEHOLDER_PATTERNS = [
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"\bTODO\b"),
    re.compile(r"\[insert", re.IGNORECASE),
    re.compile(r"\bxxx\b", re.IGNORECASE),
    # Branding-master-specific placeholder tells (resources/Dataiku Branding
    # Template 2026.pptx is heavily Lorem-Ipsum-templated; these catch a
    # forgotten replace_text_run on a base-deck-specific literal that the
    # generic patterns above wouldn't).
    re.compile(r"customer logo", re.IGNORECASE),
    re.compile(r"subtitle here if needed", re.IGNORECASE),
    re.compile(r"please try best to shorten", re.IGNORECASE),
    re.compile(r"basic slide", re.IGNORECASE),
    re.compile(r"this is a key numbers slide", re.IGNORECASE),
    re.compile(r"title of chapter", re.IGNORECASE),
]


def validate(pptx_path: Path) -> list[str]:
    """Return a list of problem descriptions; empty means all checks passed."""
    problems = []

    with zipfile.ZipFile(pptx_path, "r") as z:
        bad_entry = z.testzip()
        if bad_entry is not None:
            problems.append(f"Corrupt zip entry: {bad_entry}")
            return problems  # can't safely inspect further

        names = set(z.namelist())

        # 1. Every XML/rels part must be well-formed.
        for name in sorted(names):
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    minidom.parseString(z.read(name))
                except Exception as e:
                    problems.append(f"Malformed XML in {name}: {e}")

        if "ppt/presentation.xml" not in names or "ppt/_rels/presentation.xml.rels" not in names:
            problems.append("Missing ppt/presentation.xml or its .rels part.")
            return problems

        pres_xml = z.read("ppt/presentation.xml").decode("utf-8")
        pres_rels_xml = z.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
        ct_xml = z.read("[Content_Types].xml").decode("utf-8") if "[Content_Types].xml" in names else ""

        # 2. Every r:id in sldIdLst resolves to a relationship whose target exists.
        rids = re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>', pres_xml)
        if not rids:
            problems.append("presentation.xml has no <p:sldId> entries at all.")
        for rid in rids:
            m = re.search(rf'<Relationship Id="{re.escape(rid)}"[^>]*Target="([^"]+)"', pres_rels_xml)
            if m is None:
                problems.append(f"sldIdLst references {rid}, but it has no relationship entry.")
                continue
            target = "ppt/" + m.group(1)
            if target not in names:
                problems.append(f"Relationship {rid} points to missing part: {target}")
            slide_part = f"/{target}"
            if f'PartName="{slide_part}"' not in ct_xml:
                problems.append(f"{target} has no [Content_Types].xml Override entry.")

        # 2b. Strict readers (Keynote) reject notes parts the presentation does not declare, and a 4:3
        # size label on a page that is not 4:3.
        if any(n.startswith("ppt/notesMasters/") and n.endswith(".xml") for n in names) \
                and "<p:notesMasterIdLst>" not in pres_xml:
            problems.append("ppt/notesMasters/ exists but presentation.xml has no <p:notesMasterIdLst>; "
                            "Keynote rejects the file.")
        m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"[^>]*\btype="screen4x3"', pres_xml)
        if m and int(m.group(1)) * 3 != int(m.group(2)) * 4:
            problems.append('presentation.xml sldSz says type="screen4x3" but the page is not 4:3.')

        # 3. No leftover placeholder text on any slide actually included in the deck.
        included_slides = set()
        for rid in rids:
            m = re.search(rf'<Relationship Id="{re.escape(rid)}"[^>]*Target="([^"]+)"', pres_rels_xml)
            if m:
                included_slides.add("ppt/" + m.group(1))
        for slide_part in sorted(included_slides):
            if slide_part not in names:
                continue
            text = z.read(slide_part).decode("utf-8")
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(text):
                    problems.append(f"Placeholder-looking text ({pattern.pattern}) still present in {slide_part}")

    return problems


MANUAL_QA_CHECKLIST_V1 = """
Automated visual QA is not available, so please open the generated deck in PowerPoint/Keynote/Google
Slides and manually check:
  - Card and table text is not overflowing its shape/slide (long checklist
    text was truncated to a fixed character budget, not auto-shrunk to fit
    -- fixed card heights and computed column widths/row heights are
    estimates, not rendered-and-verified). Check both a page with a full
    slide's worth of cards/rows and a page with just 1-2.
  - The Table of Contents matches the 3 divider slides' titles (the TOC's
    2 unused slots are left blank by design, not removed).
  - The Executive Summary KPI tiles show the right count in the right
    status color (Pass=teal, Fail=red-orange, Partial=orange, Needs
    Review=peach, Not Applicable=gray), and the Top Risk callout (if
    present) reads sensibly.
  - The Results by Section scorecard's 5 status columns are colored
    consistently with the KPI tiles.
  - Status colors are consistent everywhere they appear: Critical Findings
    card IDs, Section Detail card IDs/status pills or fallback table cells,
    and the Other Must-Have Items table's Status column.
  - At least one Section Detail slide uses the card layout and, if any
    section has enough flagged items, at least one uses the table fallback
    -- both should read cleanly with the status line above them.
  - No placeholder text (Lorem ipsum, "Basic slide", etc.) remains anywhere.
  - The closing slide's Next Steps list and the Recommendations cards read
    sensibly and aren't duplicated confusingly.
""".strip()

MANUAL_QA_CHECKLIST_V2 = """
Automated visual QA is not available, so please open the generated deck in
PowerPoint/Keynote/Google Slides and manually check:
  - Text is not overflowing its card/shape on any slide (card and table
    sizes are estimates, not rendered-and-verified). Check the verdict,
    risk, quick-wins, owners and roadmap slides first.
  - Every figure on the verdict and snapshot slides matches the checklist
    (counts, applicable total, N/A exclusions).
  - Status colors are consistent everywhere they appear (stacked bar,
    risk cards, appendix tables).
  - The narrative's wording reads sensibly on each slide and every ID it
    cites is a real checklist item.
  - The appendix (method, passed checks, per-section findings, N/A items)
    reads cleanly, including a page with just 1-2 rows.
  - No placeholder text (Lorem ipsum, "Basic slide", etc.) remains anywhere.
""".strip()

# Kept for callers that don't know the deck style: the v2 deck is the default.
MANUAL_QA_CHECKLIST = MANUAL_QA_CHECKLIST_V2


def manual_qa_checklist(style: str | None = None) -> str:
    """The manual visual-QA text for a registered style (default: styles.DEFAULT_STYLE)."""
    import styles
    return styles.get_style(style or styles.DEFAULT_STYLE).qa_checklist()


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("--version", "-V"):
        print(f"validate_deck.py {common.VERSION}")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage: python3 validate_deck.py <path-to-deck.pptx>", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    problems = validate(path)
    if problems:
        print(f"FAILED structural validation for {path} ({len(problems)} issue(s)):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"OK: {path} passed all structural checks.")
    print()
    print(MANUAL_QA_CHECKLIST)
