# EMMA

EMergency Management App: a web app and an iOS app for emergency management at the University of Illinois.

Nothing is built yet: this README records the decisions made so far.

## Repository layout

| Folder | Contents |
| --- | --- |
| `LICENSE` | The MIT License, which EMMA is released under |
| `doc/` | Project documentation. `doc/config.md` describes the tech stack, with a diagram |
| `data/` | Source content: Markdown, YAML and SQLite |
| `data/md/` | Markdown documents, including Mermaid diagrams |
| `data/md/template/ics/` | Blank Incident Command System form templates, such as `ics-207.md` |
| `data/md/incident/active/yyyy-mm-dd-####/` | One folder per active incident, with its filled-in forms (for example `ics-207.md`) |
| `data/yaml/` | YAML configuration and structured content |
| `data/yaml/app.yaml` | App settings, such as the iOS bundle ID |
| `data/yaml/template/iap.yaml` | The Incident Action Plan (IAP) template: shared incident details and the list of forms |
| `data/yaml/incident/active/yyyy-mm-dd-####/` | One folder per active incident, with its filled-in `iap.yaml` |
| `data/schema/app.schema.json` | The schema `app.yaml` is checked against |
| `data/schema/iap.schema.json` | The schema every `iap.yaml` is checked against |
| `data/schema/` | JSON Schemas for the YAML files, from which the Python, JavaScript and Swift types are generated |
| `data/sqlite/` | SQLite databases, created and updated by `tools/` |
| `tools/` | Python scripts: data processing and the content build |
| `tools/install.py` | Checks for and installs everything the project needs |
| `tools/publish.py` | Publishes content as web pages. `--iap` builds `web/iap/index.html` from an Incident Action Plan |
| `bundle/` | The content bundle built by `tools/` (HTML, PNG diagrams, JSON, SQLite), used by both apps. Don't edit it by hand |
| `bundle/iap/diagrams/` | PNGs of the IAP's Mermaid diagrams for the iOS app, written by `tools/publish.py --iap` |
| `api/` | The Python API that the web app uses to read the SQLite databases |
| `web/` | The web app: plain HTML, CSS and JavaScript |
| `web/index.html` | The web app's home page, with a link to the Incident Action Plan. Written by hand, with the same toolkit page layout and header as the built pages |
| `web/iap/index.html` | The Incident Action Plan page, built by `tools/publish.py --iap`. Don't edit it by hand |
| `web/iap/diagrams/` | PNGs of the IAP's Mermaid diagrams for the web page, written by `tools/publish.py --iap` |
| `ios/` | The iOS app, in Swift |

`.gitignore` keeps Python cache files, macOS `.DS_Store` files, Xcode user data and build output, SQLite journal files and APNs keys (`*.p8`) out of the repository.

Each folder has a short README describing its purpose. Git does not track empty folders, so those files also keep the folders in the repository.

## Setup

Run `python3 tools/install.py` to check for everything the project needs. It reports what is installed and offers to install anything missing or upgrade anything too old, asking before each one. Use `--check` to only report, or `--yes` to install without asking. It uses Homebrew on macOS, apt on Debian/Ubuntu Linux, and winget on Windows. It runs on the Python 3.9 built into macOS, because it is what installs a newer Python.

| Requirement | Used for |
| --- | --- |
| Homebrew (macOS only) | Installing the other requirements on macOS. Installed with the official script from brew.sh if missing |
| Python 3.13 or newer | The scripts in `tools/` and the API in `api/`. If only an older Python is found, the script offers to install the latest with Homebrew |
| pandoc | Converting Markdown in `data/md/` to HTML in `bundle/` |
| PyYAML (Python package) | Reading the YAML in `data/yaml/`. Installed with pip for the project's Python |
| jsonschema (Python package) | Checking the YAML against the schemas in `data/schema/`. Installed with pip for the project's Python |
| Node.js 20 or newer | Running mermaid-cli, the only non-Python step of the build |
| mermaid-cli (`mmdc`) 12 or newer | Rendering Mermaid diagrams to PNG. Installed with npm; it downloads its own headless Chrome the first time. Version 12 includes the ELK layout |
| Xcode (macOS only) | Building and running the iOS app. Comes only from the Mac App Store: the script opens its page there. The Command Line Tools alone are not enough. If Xcode is installed but not selected, the script prints the `xcode-select` command to switch to it |

When the project needs something new, add it to the `REQUIREMENTS` list in `tools/install.py` and to the table above.

## Decisions

- **License:** MIT License, copyright 2026 The Board of Trustees of the University of Illinois; the full text is in `LICENSE`. Every code file starts with the University's copyright and license header, in the file's own comment style: `/* ... */` for Swift, JavaScript and CSS, `#` lines for Python (after the `#!` line), and `<!-- ... -->` for HTML. `tools/publish.py` adds it to every page it builds. JSON files can't hold comments, so the schemas have no header.
- **Languages:** Swift for the iOS app, as much of it as possible. Python for all backend data processing and the API. JavaScript, not PHP, for the web app.
- **Why JavaScript, not PHP:** neither language keeps the web app in step with Swift by itself; sharing the same data files and the same built HTML does that. JavaScript is chosen because Mermaid runs only in JavaScript, and the same code can run in the browser and, if needed, in the iOS app's web views.
- **Web stack:** plain HTML, CSS and JavaScript with no build step. Responsive CSS for computer monitors and phones.
- **Illinois Web Components Toolkit (v3):** all HTML EMMA produces (the bundle's pages, the web app, and pages shown in the iOS app) uses the University's toolkit. Getting started: https://builder3.toolkit.illinois.edu/getting_started/index.html; component specifications: https://builder3.toolkit.illinois.edu/component/index.html. Every page loads `toolkit.css` and `toolkit.js` (as a module) from `cdn.toolkit.illinois.edu/3/`; since v3.1.0 `toolkit.css` also loads the required campus stylesheet. Pages should also have the campus skip-to link and the GDPR cookie banner. Use toolkit components and classes before writing our own CSS. This replaces the earlier rule of no external CDNs.
  - **Version:** always the latest v3 release (`/3/` in the address), not a pinned version.
  - **Web:** loads the toolkit from its CDN, with the campus header and footer from the Illinois Branding CDN (`cdn.brand.illinois.edu`).
  - **iOS:** no campus header or footer. To work offline, the app uses a downloaded copy of the toolkit in `bundle/toolkit/`, with everything it loads (the campus stylesheet, fonts and any further scripts). Every build checks the CDN and downloads the files again if they have changed, so the copy is always the current release. If the CDN can't be reached, the build warns and keeps the existing copy.
- **Web app is online only:** no offline mode, no service worker and no SQLite in the browser. The web app reads data through the Python API in `api/` (FastAPI proposed).
- **ICS forms:** each Incident Command System form has a blank template in `data/md/template/ics/`, named after the form (`ics-207.md`). For an activation it is copied into the incident's folder, `data/md/incident/active/yyyy-mm-dd-####/`, and filled in there; the template itself is never filled in.
- **Incident Action Plan (IAP):** `data/yaml/template/iap.yaml` holds the details every form shares (incident name and number, operational period, who prepared and approved the plan) and lists the plan's forms in order, each with `include: true` or `false`. Its forms are ICS 202, 203, 204, 205, 205A, 206, 207, 208 and 220. ICS 201 (Incident Briefing) and ICS 214 (Activity Log) are not part of the plan but have templates for use on their own. Each form is a Markdown template in `data/md/template/ics/` following the FEMA ICS forms (v3): the same numbered blocks, as headings and tables. For an activation, `iap.yaml` is copied to `data/yaml/incident/active/yyyy-mm-dd-####/` and the forms to `data/md/incident/active/yyyy-mm-dd-####/`, and both are filled in there.
- **Publishing the IAP:** `python3 tools/publish.py --iap` builds `web/iap/index.html` from the IAP template; `--iap data/yaml/incident/active/<yyyy-mm-dd-####>/iap.yaml` builds it from an incident's IAP instead, with its forms from the same folder under `data/md/`. It checks the YAML against `data/schema/iap.schema.json`, takes the forms with `include: true` in order, fills in the `{{ ... }}` fields, renders every Mermaid diagram to a PNG with mermaid-cli, saved in `web/iap/diagrams/` for the page and `bundle/iap/diagrams/` for the iOS app (old PNGs are removed); the page shows each PNG, except that an organization chart (a flowchart that is a tree, such as ICS 207's) is drawn with the toolkit's `ilw-org-chart`, keeping each box's outline color (4 pt, drawn inside the box) and the italic *To Be Assigned*, with its PNG shown until the chart has drawn, so the chart still appears if the toolkit can't load. Each PNG has alt text (an organization chart's lists every box and who reports to whom); converts each form with pandoc, writes one page: a summary of the incident and plan, a list of the forms linking to each, then each form in turn. The page uses the Illinois Web Components Toolkit from its CDN (`ilw-page`, `ilw-header`, `ilw-footer`, `ilw-content`, whose styles cover the tables), with the SkipTo link, following the toolkit's generic HTML template. The page shows the source file but no build time, so rebuilding unchanged content changes nothing in Git.
- **Shared fields in forms:** `{{ incident.name }}`, `{{ incident.number }}`, `{{ operational_period.start }}` and `{{ operational_period.end }}` in a form are filled in by the build from the incident's `iap.yaml`, so those details are typed once. People's names default to *To Be Assigned*.
- **ICS 207 (Incident Organization Chart):** a Mermaid flowchart. Incident Command at the top, with the Operations, Logistics and Planning Section Chiefs and the RTIC Supervisor reporting to it. Each box has a 4 pt outline in a campus color: Incident Command `il-prairie` (#006230), Operations `il-orange` (#ff5f05), Logistics `il-harvest` (#fcb316), Planning `il-arches` (#009fd4), RTIC Supervisor `il-berry` (#5c0e41). Each box shows the role, then the person's name; in the template the name is *To Be Assigned* in italics, replaced with the assigned person's name (not in italics) when filled in.
- **Data formats:** all data is in SQLite databases, Markdown (including Mermaid) and YAML.
- **One build for both apps:** Python in `tools/` builds the content bundle in `bundle/`, and both apps use it, so they always show the same content:
  - Markdown becomes HTML with pandoc.
  - Mermaid diagrams are rendered to PNG ahead of time with mermaid-cli (at twice their display size, on white, so text stays sharp on high-resolution screens), so they appear instantly, look the same everywhere and work offline on iOS. The same PNGs are used by the web app and the iOS app.
  - YAML becomes JSON, checked against the schemas in `data/schema/`.
  - The SQLite databases are created and updated.
- **Mermaid ELK layout:** diagrams can use `layout: elk` in their config. Mermaid 12 and newer include ELK, so the separate `@mermaid-js/layout-elk` package is not needed; `tools/install.py` requires mermaid-cli 12 or newer. Marked 3 bundles Mermaid 12 too.
- **Shared types:** Python, JavaScript and Swift types are generated from the JSON Schemas (for example with quicktype), so field names stay the same in every language.
- **iOS app:**
  - SwiftUI for everything interactive: alerts, check-ins, forms, maps and notifications.
  - Rendered documents and diagrams are shown in a `WKWebView` from the bundle's HTML, rather than a second Markdown renderer in Swift.
  - The SQLite databases are kept on the device and read with GRDB.swift, so the app works offline during an outage.
  - Swift reads the bundle's JSON with `Codable`, so no YAML library is needed on iOS.
- **Notifications:** the Python API sends push notifications to the iOS app through Apple's Push Notification service (APNs), signed with an APNs key (`.p8`, never committed). Urgent alerts are time-sensitive; Critical Alerts need an entitlement from Apple. Details in `doc/config.md`.
- **iOS bundle ID:** `edu.illinois.emma` (in `data/yaml/app.yaml`), in the University's reversed-domain style, chosen now so it doesn't have to change when the app moves from a free Personal Team to the University's Apple Developer account (Apple treats a new bundle ID as a different app). Confirm with Technology Services that it fits their naming before registering it.
- **Apple Developer account:** not needed to start. A free Personal Team in Xcode can build in the Simulator and run on your own iPhone (installs expire after 7 days). The paid account, ideally the University's, is needed for push notifications through APNs, the Critical Alerts entitlement, TestFlight and the App Store.
- **Why an iOS app as well as the web app:** dependable push alerts (and Critical Alerts, with Apple's approval), offline access and background location. These are weak or missing in a web app on iPhone.
- **Rokwire:** later, EMMA may also be offered on iOS and Android through Rokwire, the platform behind the Illinois app. Rokwire apps are Flutter, not Swift, so this would use the same API and content bundle but separate app code. For now EMMA is a standalone web app and Swift iOS app. See `doc/config.md`.

## Open questions

- **GitHub account:** EMMA is on the jasonheimbaugh account. The University of Illinois System Shared GitHub Service (github.illinois.edu) is available to all employees if it should move there.
- **Hosting:** where the API and web app run, and behind which sign-in (for example, University NetID).
- **Android:** not planned.

## Change log

- **2026-11-25:** `web/index.html`: home page with a link to the Incident Action Plan.
- **2026-11-25:** MIT License (`LICENSE`), and the University's copyright and license header in every code file and in the pages `tools/publish.py` builds.
- **2026-11-25:** iOS bundle ID `edu.illinois.emma`, in `data/yaml/app.yaml` with its schema. When the Apple Developer account is needed, recorded in Decisions.
- **2026-11-25:** Mermaid diagrams are rendered to PNG, not SVG, for both the web and iOS. `tools/publish.py --iap` writes them to `web/iap/diagrams/` and `bundle/iap/diagrams/`; an organization chart's PNG is shown until `ilw-org-chart` has drawn it.
- **2026-11-25:** `tools/publish.py` draws organization charts (Mermaid flowcharts that are trees, such as ICS 207's) with the toolkit's `ilw-org-chart` instead of an SVG. The Markdown keeps the Mermaid chart, which Marked 3 and the iOS app still use.
- **2026-11-25:** `tools/publish.py --iap`: builds `web/iap/index.html` from the IAP template or an incident's IAP. `tools/install.py` checks for PyYAML and jsonschema.
- **2026-11-25:** ICS 207 matches the other forms: incident and operational period fields, the organization chart as block 3 (ELK layout, redux theme, roles on two lines) and Prepared by. Template edits and the chart are otherwise unchanged.
- **2026-11-25:** ICS 201 and ICS 214 removed from the IAP; their templates stay in `data/md/template/ics/`.
- **2026-11-25:** Incident Action Plan template, `data/yaml/template/iap.yaml`, with its schema, and Markdown templates for ICS 201, 202, 203, 204, 205, 205A, 206, 208, 214 and 220 alongside the existing ICS 207.
- **2026-11-25:** `tools/install.py` requires mermaid-cli 12 or newer, whose Mermaid includes the ELK layout; no separate layout-elk package is needed.
- **2026-11-25:** `doc/config.md`: notifications through Apple's Push Notification service (APNs), with a sequence diagram, setup, and the kinds of notification. `.gitignore` excludes APNs keys.
- **2026-11-23:** ICS 207: "RTIC" renamed "RTIC Supervisor". The blank-line workarounds for equal box sizes were removed.
- **2026-11-23:** `data/md/template/ics/ics-207.md`: the ICS 207 organization chart template, a Mermaid flowchart with brand-colored outlines. Folders for ICS templates and active incidents.
- **2026-11-23:** Toolkit questions settled: always the latest v3; campus header and footer on the web app only; the iOS app uses a copy in `bundle/toolkit/`, checked against the CDN and refreshed on every build.
- **2026-11-23:** All HTML uses the Illinois Web Components Toolkit (v3), loaded from its CDN. Open questions added on version pinning, offline use on iOS, and the campus header and footer.
- **2026-11-23:** `doc/config.md`: the tech stack, with a Mermaid diagram of how YAML, Markdown and SQLite are built into the bundle and used by the web app, the iOS app and a future Rokwire app.
- **2026-11-20:** `tools/install.py` notices when Xcode is installed but the Command Line Tools are selected, and prints the command to switch.
- **2026-11-20:** `tools/install.py`: checks for and installs Homebrew, Python 3.13, pandoc, Node.js, mermaid-cli and Xcode.
- **2026-11-20:** New repository. Folder structure and READMEs; decisions on languages, data formats, the shared content build and the iOS app.
