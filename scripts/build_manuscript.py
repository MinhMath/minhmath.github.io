#!/usr/bin/env python3
"""Archive every revision of the LaTeX source published at /o."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/o"
SOURCE = "docs/o/mr_area_revised.tex"
ARCHIVE = PAGE / "versions"
PDF_CACHE = ROOT / ".manuscript-pdf"
TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def compile_pdf(source, target):
    with TemporaryDirectory(prefix="manuscript-") as directory:
        work = Path(directory)
        tex = work / "manuscript.tex"
        tex.write_bytes(source)
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode",
                 "-halt-on-error", "-file-line-error", tex.name],
                cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", timeout=120,
            )
            if result.returncode:
                raise RuntimeError("\n".join(result.stdout.splitlines()[-24:]))
        pdf = (work / "manuscript.pdf").read_bytes()
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(pdf)
        temporary.replace(target)


def version_row(name, stamp, latest, has_pdf):
    label = "Latest version" if latest else "Earlier version"
    display_time = f"{stamp.day} {stamp:%B %Y, %H:%M:%S} (Vietnam time)"
    description = f"version-{name}"
    url = f"/o/versions/{name}"
    pdf_action = (
        f'<a class="pdf-action" href="{url}.pdf" aria-describedby="{description}">View PDF</a>'
        if has_pdf else '<span>PDF unavailable</span>'
    )
    return f'''      <li>
        <div class="version-row">
          <div id="{description}">
            <strong>{label}</strong>
            <time datetime="{stamp.isoformat()}">{display_time}</time>
          </div>
          <div class="version-actions">
            <button type="button" aria-describedby="{description}" data-source="{url}.tex" disabled>Copy LaTeX</button>
            {pdf_action}
          </div>
        </div>
        <p class="copy-status" role="status"></p>
      </li>'''


def main():
    history = git("log", "--first-parent", "--diff-filter=AM", "--format=%H%x09%cI", "--", SOURCE)
    revisions = [line.split("\t") for line in history.decode().splitlines()]
    if not revisions:
        raise RuntimeError(f"No published revisions of {SOURCE} were found.")
    revisions.sort(key=lambda entry: datetime.fromisoformat(entry[1]), reverse=True)
    ARCHIVE.mkdir(exist_ok=True)
    PDF_CACHE.mkdir(exist_ok=True)
    rows = []
    all_pdfs_ready = True
    for commit, timestamp in revisions:
        stamp = datetime.fromisoformat(timestamp).astimezone(TIMEZONE)
        name = f"{stamp:%Y-%m-%d-%H%M%S}-{commit[:12]}"
        revision = f"{commit}:{SOURCE}"
        blob = git("rev-parse", revision).decode().strip()
        source = git("cat-file", "blob", blob)
        (ARCHIVE / f"{name}.tex").write_bytes(source)
        cached_pdf = PDF_CACHE / f"{blob}.pdf"
        has_pdf = True
        try:
            if not cached_pdf.is_file():
                compile_pdf(source, cached_pdf)
            (ARCHIVE / f"{name}.pdf").write_bytes(cached_pdf.read_bytes())
            print(f"PDF ready for {name}", flush=True)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            print(f"Could not compile revision {commit}\n{error}", flush=True)
            has_pdf = False
            all_pdfs_ready = False
        rows.append(version_row(name, stamp, not rows, has_pdf))

    page = PAGE / "index.html"
    template = page.read_text(encoding="utf-8")
    begin = "<!-- BEGIN MANUSCRIPT VERSIONS -->"
    end = "<!-- END MANUSCRIPT VERSIONS -->"
    before, separator, remainder = template.partition(begin)
    _, closing, after = remainder.partition(end)
    if not separator or not closing:
        raise RuntimeError("The manuscript page is missing its version list markers.")
    page.write_text(before + begin + "\n" + "\n".join(rows) + "\n      " + end + after, encoding="utf-8")
    if output := os.getenv("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as output_file:
            print(f"pdfs_ready={str(all_pdfs_ready).lower()}", file=output_file)


if __name__ == "__main__":
    main()
