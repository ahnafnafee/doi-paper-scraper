# Academic Paper API

Scrape academic papers by DOI and reconstruct them as Markdown — with full text content, images, and figure placement.

## Features

- **Flexible DOI input**: accepts plain DOIs, `doi.org` URLs, `dx.doi.org` URLs, publisher URLs, or any string containing a DOI
- **Cloudflare bypass**: uses [pydoll](https://github.com/autoscrape-labs/pydoll) for stealth browser automation
- **Publisher-specific scrapers**: ACM Digital Library, IEEE Xplore (extensible)
- **Image downloading**: saves figures locally with original placement preserved
- **Markdown output**: reconstructed paper with headings, paragraphs, lists, and inline figures
- **Institutional login**: supports cookies for authenticated access to paywalled content

## Installation

Requires Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and install
git clone https://github.com/yourusername/academic-paper-api.git
cd academic-paper-api
uv sync
```

## Usage

```bash
# Plain DOI
uv run paper-scrape 10.1145/3746059.3747603

# DOI URL
uv run paper-scrape "https://doi.org/10.1145/3746059.3747603"

# Publisher URL
uv run paper-scrape "https://dl.acm.org/doi/10.1145/3746059.3747603"

# With custom output directory
uv run paper-scrape 10.1145/3746059.3747603 --output-dir ./my_papers

# With institutional login cookies
uv run paper-scrape 10.1145/3746059.3747603 --cookies cookies.json
```

## Cookies for Institutional Access

To use your institutional login (e.g., George Mason University):

1. Install a browser extension like [Cookie-Editor](https://cookie-editor.com/) or [EditThisCookie](https://www.editthiscookie.com/)
2. Log in to the publisher site through your institution's proxy
3. Export cookies as JSON
4. Save to a file (e.g., `cookies.json`)
5. Pass with `--cookies cookies.json`

## Output

The tool creates:
```
output/
├── Paper_Title.md     # Reconstructed paper in Markdown
└── images/            # Downloaded figures
    ├── fig_abc123.jpg
    └── fig_def456.jpg
```

## Supported Publishers

| Publisher | DOI Prefix | Status |
|-----------|-----------|--------|
| ACM Digital Library | `10.1145` | ✅ Implemented |
| IEEE Xplore | `10.1109` | ✅ Implemented |

## License

MIT
