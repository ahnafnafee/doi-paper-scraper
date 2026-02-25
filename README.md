# DOI Paper Scraper - Extract Academic Papers to Markdown

**Automated research paper extraction tool for academics and developers.** Scrape academic papers from ACM Digital Library, IEEE Xplore, and other publishers using DOI. Convert papers to structured Markdown with full-text content, figures, tables, and institutional access support.

### What is DOI Paper Scraper?

A Python command-line tool that automates the extraction of academic research papers from digital libraries. Download papers by Digital Object Identifier (DOI), convert them to clean Markdown format, and extract figures with original placement preserved. Ideal for research automation, bibliography management, content analysis, and building research databases.

## Key Features

- **DOI Resolution**: accepts plain DOIs, `doi.org` URLs, `dx.doi.org` URLs, publisher direct links, or any string containing a Digital Object Identifier
- **Cloudflare Bypass**: uses [pydoll](https://github.com/autoscrape-labs/pydoll) for intelligent browser automation to access protected content
- **Academic Publisher Support**: built-in scrapers for ACM Digital Library, IEEE Xplore (easily extensible for Springer, Elsevier, etc.)
- **Content Extraction**: preserves full paper structure including headings, paragraphs, lists, tables, and citations
- **Figure & Image Extraction**: automatically downloads figures, diagrams, and images with original placement preserved in output
- **Markdown Conversion**: converts academic papers to clean, readable Markdown format perfect for research tools, documentation, and archival
- **Institutional Authentication**: supports proxy and institutional login via browser cookies for accessing paywalled academic journals
- **Batch Processing Ready**: command-line interface designed for automation and integration into research workflows

## Why Use DOI Paper Scraper?

- **Research Automation**: Build automated pipelines for literature review and citation tracking
- **Knowledge Base Building**: Extract papers into searchable Markdown databases
- **Content Analysis**: Convert PDFs to machine-readable text for NLP and text analysis
- **Offline Access**: Create persistent Markdown copies of academic papers for offline research
- **Data Mining**: Programmatically extract research data from scholarly articles
- **Academic Accessibility**: Easy access to papers through institutional login support
- **Open Source**: Free and extensible tool for researchers and developers

## Installation & Setup

Requires Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/) package manager.

```bash
# Clone the repository
git clone https://github.com/ahnafnafee/doi-paper-scraper.git
cd doi-paper-scraper

# Install dependencies
uv sync
```

## Quick Start - Usage Examples

Extract papers using Digital Object Identifiers (DOIs) in multiple formats:

```bash
# Extract by plain DOI
uv run paper-scrape 10.1145/3746059.3747603

# Extract from DOI.org URL
uv run paper-scrape "https://doi.org/10.1145/3746059.3747603"

# Extract from ACM Digital Library direct link
uv run paper-scrape "https://dl.acm.org/doi/10.1145/3746059.3747603"

# Extract from IEEE Xplore direct link
uv run paper-scrape "https://ieeexplore.ieee.org/document/1234567"

# Save to custom directory with folder organization
uv run paper-scrape 10.1145/3746059.3747603 --output-dir ./research_papers

# Extract with institutional login (for paywalled access)
uv run paper-scrape 10.1145/3746059.3747603 --cookies cookies.json
```

## Accessing Paywalled Papers - Institutional Login

Access restricted academic content from your institution (university, research center, corporate research lab):

1. Install a browser extension like [Cookie-Editor](https://cookie-editor.com/) or [EditThisCookie](https://www.editthiscookie.com/)
2. Log in to the academic publisher (ACM, IEEE, etc.) through your institution's proxy/VPN
3. Export cookies as JSON using the browser extension
4. Save to a file (e.g., `cookies.json`)
5. Use with DOI Paper Scraper: `uv run paper-scrape [DOI] --cookies cookies.json`

**Example institutions**: George Mason University, MIT, Stanford, UC Berkeley, and any university with library proxy access.

## Output Format

DOI Paper Scraper creates organized output with extracted content:

```
output/
├── Paper_Title.md          # Full paper in Markdown format (text-searchable)
└── images/                 # All figures, diagrams, and tables
    ├── figure_1.jpg       # Figures numbered and labeled
    ├── figure_2.png
    └── table_data.jpg
```

**Benefits of Markdown output**:

- Text-searchable format (unlike PDFs)
- Git-friendly for version control
- Easy to integrate into documentation systems
- Compatible with static site generators (Hugo, MkDocs, Jekyll)
- Preserves structure and formatting for readability

## Supported Academic Publishers & DOI Prefixes

| Publisher           | DOI Prefix | Status         | Coverage                                 |
| ------------------- | ---------- | -------------- | ---------------------------------------- |
| ACM Digital Library | `10.1145`  | ✅ Implemented | Computing, algorithms, HCI               |
| IEEE Xplore         | `10.1109`  | ✅ Implemented | Electrical engineering, computer science |
| Springer            | `10.1007`  | 🔄 Planned     | Physics, mathematics, computer science   |
| Elsevier            | `10.1016`  | 🔄 Planned     | All scientific disciplines               |

**Want to add more publishers?** The tool is designed as an extensible framework—contributions welcome!

## Use Cases & Applications

### Academic & Research

- Literature review automation
- Citation network analysis
- Systematic review data extraction
- Research paper archival and backup

### Development & Integration

- Build research knowledge bases
- Create searchable paper databases
- Extract metadata for research tools
- Integrate with academic project pipelines

### Content & Data Processing

- Convert papers to training data for ML models
- Text analysis and NLP experiments
- Content analysis and information extraction
- Bibliography and reference management

## License

MIT License - Free for academic and commercial use
