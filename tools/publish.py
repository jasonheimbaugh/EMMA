#!/usr/bin/env python3
"""Publish EMMA content as web pages.

Usage:
  python3 tools/publish.py --iap
      Build web/iap/index.html from the IAP template, data/yaml/template/iap.yaml.
  python3 tools/publish.py --iap data/yaml/incident/active/<yyyy-mm-dd-####>/iap.yaml
      Build it from an incident's IAP instead.

What --iap does:
  1. Reads the IAP YAML and checks it against data/schema/iap.schema.json.
  2. Takes the forms it lists with include: true, in order, from
     data/md/template/ics/ (for the template) or from the incident's folder
     under data/md/incident/active/ (for an incident).
  3. Fills in {{ incident.name }}, {{ incident.number }},
     {{ operational_period.start }} and the other {{ ... }} fields from the YAML.
  4. Renders each Mermaid diagram to SVG with mermaid-cli (mmdc).
  5. Converts each form's Markdown to HTML with pandoc.
  6. Writes one page, web/iap/index.html, built with the Illinois Web
     Components Toolkit (v3) from its CDN, with the campus header and footer.

Needs Python 3.13 or newer, PyYAML, jsonschema, pandoc and mermaid-cli 12 or
newer: run python3 tools/install.py to check for them.

To pass a puppeteer configuration file to mermaid-cli (for example, to use a
particular Chrome), set MMDC_PUPPETEER_CONFIG to its path.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IAP_TEMPLATE = ROOT / "data/yaml/template/iap.yaml"
IAP_SCHEMA = ROOT / "data/schema/iap.schema.json"
TEMPLATE_FORMS = ROOT / "data/md/template/ics"
YAML_DIR = ROOT / "data/yaml"
MD_DIR = ROOT / "data/md"
IAP_OUTPUT = ROOT / "web/iap/index.html"

TOOLKIT = "//cdn.toolkit.illinois.edu/3"
SITE_NAME = "EMMA"

# A ```mermaid ... ``` block in Markdown.
MERMAID_BLOCK = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
# A {{ dotted.name }} field.
FIELD = re.compile(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}")
# Where a diagram goes in pandoc's output (pandoc keeps raw HTML in Markdown).
DIAGRAM_MARK = '<div data-emma-diagram="{n}"></div>'
DIAGRAM_MARK_RE = re.compile(r'<div data-emma-diagram="(\d+)"></div>')


def fail(message: str) -> None:
    print(f"publish: {message}", file=sys.stderr)
    sys.exit(1)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def need(command: str) -> str:
    found = shutil.which(command)
    if not found:
        fail(f"'{command}' was not found. Run python3 tools/install.py.")
    return found


# ---------------------------------------------------------------- reading

def load_iap(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        fail("PyYAML is not installed. Run python3 tools/install.py.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{rel(path)} does not exist.")
    except yaml.YAMLError as e:
        fail(f"{rel(path)} is not valid YAML: {e}")

    try:
        import jsonschema
    except ImportError:
        fail("jsonschema is not installed. Run python3 tools/install.py.")
    schema = json.loads(IAP_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"  {'/'.join(map(str, e.path)) or '(top)'}: {e.message}" for e in errors]
        fail(f"{rel(path)} does not match {rel(IAP_SCHEMA)}:\n" + "\n".join(lines))
    return data


def forms_folder(iap_path: Path) -> Path:
    """Where the forms for this IAP are: the template folder for the template,
    otherwise the same folder under data/md/ as the YAML's under data/yaml/."""
    if iap_path.resolve() == IAP_TEMPLATE.resolve():
        return TEMPLATE_FORMS
    try:
        return MD_DIR / iap_path.resolve().parent.relative_to(YAML_DIR.resolve())
    except ValueError:
        fail(f"{rel(iap_path)} is not under {rel(YAML_DIR)}, so its forms can't be found.")


def fill_fields(text: str, data: dict, source: str) -> str:
    """Replace each {{ dotted.name }} with its value from the IAP YAML."""
    def value(match: re.Match) -> str:
        node = data
        for part in match.group(1).split("."):
            if not isinstance(node, dict) or part not in node:
                print(f"publish: warning: {source}: no value for {{{{ {match.group(1)} }}}}", file=sys.stderr)
                return match.group(0)
            node = node[part]
        return "" if node is None else str(node)
    return FIELD.sub(value, text)


# ---------------------------------------------------------------- converting

def render_diagrams(markdown: str, slug: str, workdir: Path) -> tuple[str, list[str]]:
    """Render each Mermaid block to SVG and replace it with a marker.
    Returns the Markdown and the SVGs, in order."""
    mmdc = need("mmdc")
    svgs: list[str] = []

    def render(match: re.Match) -> str:
        n = len(svgs)
        source = workdir / f"{slug}-{n}.mmd"
        output = workdir / f"{slug}-{n}.svg"
        source.write_text(match.group(1), encoding="utf-8")
        cmd = [mmdc, "-q", "-i", str(source), "-o", str(output), "-I", f"{slug}-diagram-{n}", "-b", "transparent"]
        if os.environ.get("MMDC_PUPPETEER_CONFIG"):
            cmd += ["-p", os.environ["MMDC_PUPPETEER_CONFIG"]]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not output.exists():
            fail(f"mermaid-cli could not render diagram {n + 1} in {slug}:\n{result.stderr.strip()}")
        svg = output.read_text(encoding="utf-8")
        svgs.append(svg[svg.index("<svg"):])  # drop any XML declaration
        return "\n" + DIAGRAM_MARK.format(n=n) + "\n"

    return MERMAID_BLOCK.sub(render, markdown), svgs


def to_html(markdown: str, source: str, slug: str) -> str:
    """Convert Markdown to an HTML fragment with pandoc. Headings move down one
    level, because the page has its own h1, and heading ids start with the form's
    slug, so they are unique on the page."""
    pandoc = need("pandoc")
    result = subprocess.run(
        [pandoc, "--from", "gfm", "--to", "html5", "--shift-heading-level-by=1", "--wrap=none", f"--id-prefix={slug}-"],
        input=markdown, capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"pandoc could not convert {source}:\n{result.stderr.strip()}")
    return result.stdout


def form_section(form: dict, folder: Path, data: dict, workdir: Path) -> str:
    path = folder / form["file"]
    if not path.exists():
        fail(f"{rel(path)} does not exist (listed as {form['form']} in the IAP).")
    slug = path.stem  # ics-202
    markdown = fill_fields(path.read_text(encoding="utf-8"), data, rel(path))
    markdown, svgs = render_diagrams(markdown, slug, workdir)
    body = to_html(markdown, rel(path), slug)
    body = DIAGRAM_MARK_RE.sub(
        lambda m: f'<figure class="emma-diagram">{svgs[int(m.group(1))]}</figure>', body
    )
    return f'<section id="{slug}" class="emma-form">\n<ilw-content>\n{body}</ilw-content>\n</section>'


# ---------------------------------------------------------------- the page

def summary(data: dict) -> str:
    e = html.escape
    op = data["operational_period"]
    rows = [
        ("Incident Name", data["incident"]["name"]),
        ("Incident Number", data["incident"]["number"]),
        ("Operational Period", f"{op['number']}: {op['start']} to {op['end']}" if op["start"] or op["end"] else str(op["number"])),
        ("Prepared by", f"{data['prepared_by']['name']}, {data['prepared_by']['position']}"),
        ("Approved by", f"{data['approved_by']['name']}, {data['approved_by']['position']}"),
    ]
    body = "\n".join(f"<tr><th scope=\"row\">{e(a)}</th><td>{e(str(b))}</td></tr>" for a, b in rows)
    return f"<table>\n<tbody>\n{body}\n</tbody>\n</table>"


def contents(forms: list[dict]) -> str:
    e = html.escape
    items = "\n".join(
        f'<li><a href="#{Path(f["file"]).stem}">{e(f["form"])}: {e(f["title"])}</a></li>' for f in forms
    )
    return f"<h2>Forms</h2>\n<ol>\n{items}\n</ol>"


def page(title: str, main: str) -> str:
    e = html.escape
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="EMMA tools/publish.py">
<link rel="icon" href="https://cdn.brand.illinois.edu/favicon.ico">
<link rel="apple-touch-icon" href="https://cdn.brand.illinois.edu/touch-icon-40x40.png">
<link rel="apple-touch-icon" sizes="152x152" href="https://cdn.brand.illinois.edu/touch-icon-152x152.png">
<link rel="apple-touch-icon" sizes="167x167" href="https://cdn.brand.illinois.edu/touch-icon-167x167.png">
<link rel="apple-touch-icon" sizes="180x180" href="https://cdn.brand.illinois.edu/touch-icon-180x180.png">
<link rel="dns-prefetch" href="//cdn.toolkit.illinois.edu">
<link rel="dns-prefetch" href="//cdn.disability.illinois.edu">
<link rel="stylesheet" href="{TOOLKIT}/toolkit.css">
<script type="module" src="{TOOLKIT}/toolkit.js"></script>
<script src="//cdn.disability.illinois.edu/skipto.min.js"></script>
<script>var SkipToConfig = {{ 'settings': {{ 'skipTo': {{ colorTheme: 'illinois' }} }} }};</script>
<title>{e(title)} | {SITE_NAME}</title>
<style>
.emma-diagram {{ margin: 1.5rem 0; overflow-x: auto; }}
.emma-diagram svg {{ max-width: 100%; height: auto; }}
.emma-form {{ border-top: 1px solid var(--il-storm-80, #c8c6c7); padding-top: 1rem; }}
</style>
</head>
<body style="margin: 0;">
<ilw-page class="ilw-format">
<ilw-header slot="header">
<a slot="site-name" href="/">{SITE_NAME}</a>
</ilw-header>
<main id="main-content">
{main}
</main>
<ilw-footer slot="footer">
<a slot="site-name" href="/">{SITE_NAME}</a>
</ilw-footer>
</ilw-page>
</body>
</html>
"""


def publish_iap(iap_path: Path) -> None:
    data = load_iap(iap_path)
    folder = forms_folder(iap_path)
    forms = [f for f in data["forms"] if f["include"]]
    if not forms:
        fail(f"{rel(iap_path)} has no forms with include: true.")

    name = data["incident"]["name"]
    title = f"Incident Action Plan: {name}" if name else "Incident Action Plan"
    with tempfile.TemporaryDirectory() as tmp:
        sections = [form_section(f, folder, data, Path(tmp)) for f in forms]

    main = "\n".join([
        f"<ilw-content>\n<h1>{html.escape(title)}</h1>\n{summary(data)}\n{contents(forms)}\n"
        f"<p><small>Built from <code>{html.escape(rel(iap_path))}</code>.</small></p>\n</ilw-content>",
        *sections,
    ])
    IAP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    IAP_OUTPUT.write_text(page(title, main), encoding="utf-8")
    print(f"Wrote {rel(IAP_OUTPUT)}: {len(forms)} forms from {rel(iap_path)}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish EMMA content as web pages.")
    parser.add_argument(
        "--iap", nargs="?", const=str(IAP_TEMPLATE), metavar="IAP_YAML",
        help=f"build {rel(IAP_OUTPUT)} from an IAP YAML file (default: {rel(IAP_TEMPLATE)})",
    )
    args = parser.parse_args()
    if args.iap is None:
        parser.print_help()
        return 2
    path = Path(args.iap)
    publish_iap(path if path.is_absolute() else (Path.cwd() / path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
