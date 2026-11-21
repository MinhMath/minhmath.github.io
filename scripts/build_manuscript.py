#!/usr/bin/env python3
"""Archive every revision of the LaTeX source published at /o."""

import os
import subprocess
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import wrap
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


def source_changes(older, newer):
    changes = unified_diff(
        older.decode().splitlines(), newer.decode().splitlines(),
        fromfile="Previous revision", tofile="Selected revision", lineterm="",
    )
    escape = str.maketrans({
        "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "#": r"\#",
        "%": r"\%", "&": r"\&", "_": r"\_", "$": r"\$", " ": r"\ ",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
        "<": r"\textless{}", ">": r"\textgreater{}",
    })
    lines = [r"\section*{LaTeX source changes}",
             r"\noindent Blue lines were added. Red lines were removed.\par\medskip",
             r"\begingroup\ttfamily\footnotesize\setlength{\parindent}{0pt}"]
    for line in changes:
        color = "blue!70!black" if line.startswith("+") else (
            "red!75!black" if line.startswith("-") else "black"
        )
        for part in wrap(line, width=90, drop_whitespace=False):
            # Keep source commands literal, including Unicode in LaTeX comments.
            literal = part.encode("ascii", errors="backslashreplace").decode("ascii").translate(escape)
            lines.append(rf"\textcolor{{{color}}}{{{literal}}}\par")
    lines.append(r"\endgroup")
    return "\n".join(lines).encode()


def compile_diff(older, newer, target):
    appendix = source_changes(older, newer)
    try:
        with TemporaryDirectory(prefix="manuscript-diff-") as directory:
            work = Path(directory)
            (work / "old.tex").write_bytes(older)
            (work / "new.tex").write_bytes(newer)
            marked = subprocess.run(
                ["latexdiff", "--type=CFONT", "--math-markup=whole",
                 "--disable-citation-markup",
                 "--config=PICTUREENV=(?:picture|tikzpicture|DIFnomarkup)",
                 "old.tex", "new.tex"],
                cwd=work, capture_output=True, check=True, timeout=90,
            ).stdout
        end = rb"\end{document}"
        body, separator, after = marked.rpartition(end)
        if not separator:
            raise RuntimeError("The marked manuscript has no document end.")
        legend = rb"""
\par\smallskip\noindent\textbf{Revision comparison.}
\textcolor{blue}{Added or revised text.} \textcolor{red}{Removed text.}
The final pages list the LaTeX source changes, including figure code.\par\smallskip
"""
        insertion = rb"\maketitle" if rb"\maketitle" in body else rb"\begin{document}"
        body = body.replace(insertion, insertion + legend, 1)
        compile_pdf(body + b"\n" + rb"\clearpage" + b"\n" + appendix + b"\n" + end + after, target)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Using a source-only diff for {target.name}: {error}", flush=True)
        preamble = rb"""\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage{lmodern,xcolor}
\usepackage[a4paper,margin=25mm]{geometry}
\begin{document}
"""
        compile_pdf(preamble + appendix + b"\n" + rb"\end{document}" + b"\n", target)


def version_row(name, stamp, latest, has_pdf, diff_action):
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
            {diff_action}
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
    sources = [git("rev-parse", f"{commit}:{SOURCE}").decode().strip() for commit, _ in revisions]
    for index, (commit, timestamp) in enumerate(revisions):
        stamp = datetime.fromisoformat(timestamp).astimezone(TIMEZONE)
        name = f"{stamp:%Y-%m-%d-%H%M%S}-{commit[:12]}"
        blob = sources[index]
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
        diff_action = ""
        if index + 1 < len(revisions):
            previous_blob = sources[index + 1]
            cached_diff = PDF_CACHE / f"diff-{previous_blob}-{blob}.pdf"
            try:
                if not cached_diff.is_file():
                    compile_diff(git("cat-file", "blob", previous_blob), source, cached_diff)
                (ARCHIVE / f"{name}-diff.pdf").write_bytes(cached_diff.read_bytes())
                diff_action = (
                    f'<a class="pdf-action" href="/o/versions/{name}-diff.pdf" '
                    f'aria-describedby="version-{name}">View Diff PDF</a>'
                )
                print(f"Diff PDF ready for {name}", flush=True)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                print(f"Could not build diff for revision {commit}\n{error}", flush=True)
                diff_action = "<span>Diff PDF unavailable</span>"
                all_pdfs_ready = False
        rows.append(version_row(name, stamp, index == 0, has_pdf, diff_action))

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
