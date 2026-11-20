# EMMA

EMergency Management App: a web app and an iOS app for emergency management at the University of Illinois.

Nothing is built yet: this README records the decisions made so far.

## Repository layout

| Folder | Contents |
| --- | --- |
| `data/` | Source content: Markdown, YAML and SQLite |
| `data/md/` | Markdown documents, including Mermaid diagrams |
| `data/yaml/` | YAML configuration and structured content |
| `data/schema/` | JSON Schemas for the YAML files, from which the Python, JavaScript and Swift types are generated |
| `data/sqlite/` | SQLite databases, created and updated by `tools/` |
| `tools/` | Python scripts: data processing and the content build |
| `tools/install.py` | Checks for and installs everything the project needs |
| `bundle/` | The content bundle built by `tools/` (HTML, SVG, JSON, SQLite), used by both apps. Don't edit it by hand |
| `api/` | The Python API that the web app uses to read the SQLite databases |
| `web/` | The web app: plain HTML, CSS and JavaScript |
| `ios/` | The iOS app, in Swift |

`.gitignore` keeps Python cache files, macOS `.DS_Store` files, Xcode user data and build output, and SQLite journal files out of the repository.

Each folder has a short README describing its purpose. Git does not track empty folders, so those files also keep the folders in the repository.

## Setup

Run `python3 tools/install.py` to check for everything the project needs. It reports what is installed and offers to install anything missing or upgrade anything too old, asking before each one. Use `--check` to only report, or `--yes` to install without asking. It uses Homebrew on macOS, apt on Debian/Ubuntu Linux, and winget on Windows. It runs on the Python 3.9 built into macOS, because it is what installs a newer Python.

| Requirement | Used for |
| --- | --- |
| Homebrew (macOS only) | Installing the other requirements on macOS. Installed with the official script from brew.sh if missing |
| Python 3.13 or newer | The scripts in `tools/` and the API in `api/`. If only an older Python is found, the script offers to install the latest with Homebrew |
| pandoc | Converting Markdown in `data/md/` to HTML in `bundle/` |
| Node.js 20 or newer | Running mermaid-cli, the only non-Python step of the build |
| mermaid-cli (`mmdc`) | Rendering Mermaid diagrams to SVG in `bundle/`. Installed with npm; it downloads its own headless Chrome the first time |
| Xcode (macOS only) | Building and running the iOS app. Comes only from the Mac App Store: the script opens its page there. The Command Line Tools alone are not enough |

When the project needs something new, add it to the `REQUIREMENTS` list in `tools/install.py` and to the table above.

## Decisions

- **Languages:** Swift for the iOS app, as much of it as possible. Python for all backend data processing and the API. JavaScript, not PHP, for the web app.
- **Why JavaScript, not PHP:** neither language keeps the web app in step with Swift by itself; sharing the same data files and the same built HTML does that. JavaScript is chosen because Mermaid runs only in JavaScript, and the same code can run in the browser and, if needed, in the iOS app's web views.
- **Web stack:** plain HTML, CSS and JavaScript with no build step. No external CDNs or web fonts. Responsive CSS for computer monitors and phones.
- **Web app is online only:** no offline mode, no service worker and no SQLite in the browser. The web app reads data through the Python API in `api/` (FastAPI proposed).
- **Data formats:** all data is in SQLite databases, Markdown (including Mermaid) and YAML.
- **One build for both apps:** Python in `tools/` builds the content bundle in `bundle/`, and both apps use it, so they always show the same content:
  - Markdown becomes HTML with pandoc.
  - Mermaid diagrams are rendered to SVG ahead of time with mermaid-cli, so they appear instantly, look the same everywhere and work offline on iOS.
  - YAML becomes JSON, checked against the schemas in `data/schema/`.
  - The SQLite databases are created and updated.
- **Shared types:** Python, JavaScript and Swift types are generated from the JSON Schemas (for example with quicktype), so field names stay the same in every language.
- **iOS app:**
  - SwiftUI for everything interactive: alerts, check-ins, forms, maps and notifications.
  - Rendered documents and diagrams are shown in a `WKWebView` from the bundle's HTML, rather than a second Markdown renderer in Swift.
  - The SQLite databases are kept on the device and read with GRDB.swift, so the app works offline during an outage.
  - Swift reads the bundle's JSON with `Codable`, so no YAML library is needed on iOS.
- **Why an iOS app as well as the web app:** dependable push alerts (and Critical Alerts, with Apple's approval), offline access and background location. These are weak or missing in a web app on iPhone.
- **Rokwire:** set aside for now. EMMA is a standalone app, not a module of the Illinois app.

## Open questions

- **GitHub account:** EMMA is on the jasonheimbaugh account. The University of Illinois System Shared GitHub Service (github.illinois.edu) is available to all employees if it should move there.
- **Ownership and licence:** software made as part of University employment is owned by the University. Check with the Office of Technology Management (otm@illinois.edu) before releasing EMMA as open source, especially if it's grant-funded. The usual University licence is the University of Illinois/NCSA Open Source License.
- **Hosting:** where the API and web app run, and behind which sign-in (for example, University NetID).
- **Android:** not planned.

## Change log

- **2026-11-20:** `tools/install.py`: checks for and installs Homebrew, Python 3.13, pandoc, Node.js, mermaid-cli and Xcode.
- **2026-11-20:** New repository. Folder structure and READMEs; decisions on languages, data formats, the shared content build and the iOS app.
