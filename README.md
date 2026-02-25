# 📄 DOI Paper Scraper — Extract Academic Papers to Markdown 🚀

**An automated research paper extraction tool designed for academics, researchers, and developers.** 

Scrape academic papers from **ACM Digital Library**, **IEEE Xplore**, and other publishers using just a **DOI**. Convert complex academic layouts into structured, clean **Markdown** with full-text content, LaTeX equations, tables, and high-quality figures.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Key Features

- **🎯 Intelligent DOI Resolution**: Accepts plain DOIs, `doi.org` URLs, publisher direct links, or any string containing a Digital Object Identifier.
- **🛡️ Cloudflare & Anti-Bot Bypass**: Leverages [pydoll](https://github.com/autoscrape-labs/pydoll) for advanced browser automation to bypass WAFs and access protected content.
- **📚 Multi-Publisher Support**: Built-in specialized scrapers for **ACM Digital Library** and **IEEE Xplore**. Easily extensible for Springer, Elsevier, Wiley, and more.
- **📐 Rich Content Extraction**: 
  - Preserves full paper hierarchy (Headings, Sub-headings).
  - Automatically converts **MathJax/LaTeX** equations into Markdown `$math$` blocks.
  - Extracts **Figures and Tables** with original captions and placement.
- **🔗 Institutional Access Support**: Seamlessly navigate paywalls using **Institutional Proxy** redirection and **Browser Cookie** injection (supports GMU's EZProxy and others).
- **📋 Structured Output**: Generates clean, text-searchable Markdown files—perfect for research archival, NLP analysis, and building personal knowledge bases.

---

## 🛠️ Installation

This project uses the high-performance [uv](https://docs.astral.sh/uv/) package manager.

```bash
# 1. Clone the repository
git clone https://github.com/ahnafnafee/doi-paper-scraper.git
cd doi-paper-scraper

# 2. Install dependencies (creates a virtualenv automatically)
uv sync
```

---

## 🚀 Quick Usage

Extract any paper into Markdown with one command:

```bash
# Extract by plain DOI
uv run paper-scrape 10.1145/3746059.3747603

# Extract by DOI URL
uv run paper-scrape "https://doi.org/10.1109/CSCloud-EdgeCom58631.2023.00053"

# Save to a specific directory
uv run paper-scrape [DOI] --output-dir ./my_research
```

### 🏫 Accessing Paywalled Content (Institutional Login)

If you have access via a University library (e.g., George Mason University):

1. Log in to the publisher (IEEE/ACM) through your university's proxy.
2. Export your session cookies as a JSON file using a browser extension (like [Cookie-Editor](https://cookie-editor.com/)).
3. Run the scraper with the cookies and proxy flag:

```bash
uv run paper-scrape [DOI] --cookies ieee_cookies.json --proxy "https://mutex.gmu.edu/login?qurl=%u"
```

---

## 💻 CLI Reference

| Option | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--output-dir` | `-o` | Directory where papers and images will be saved. | `output/` |
| `--cookies` | `-c` | Path to a JSON cookie file for institutional authentication. | `None` |
| `--proxy` | `-p` | Proxy URL template (use `%u` for target URL). | GMU EZProxy |
| `--no-proxy` | | Disable the default proxy even if on a supported domain. | `False` |
| `--verbose` | `-v` | Enable detailed logging for debugging. | `False` |

---

## 📂 Output Structure

The tool organizes extracted data into a clean, portable structure:

```text
output/
├── Quarks_A_Secure_Messaging_Network.md   # Paper text + Markdown formatting
└── images/                                # Extracted figures, diagrams, and tables
    ├── fig_a1b2.png
    └── table_c3d4.gif
```

---

## 🧬 Why Choose DOI Paper Scraper?

- **Research Portability**: Text-searchable Markdown is 100x easier to search and edit than static PDFs.
- **Knowledge Graphs**: Perfect for importing papers into tools like **Obsidian**, **Logseq**, or **Notion**.
- **NLP Research**: Clean text extraction without the "noise" of PDF parsing (extra line breaks, headers/footers).
- **Automation**: Designed to be integrated into CI/CD pipelines or batch processing scripts.

---

## 📜 License

Distributed under the **MIT License**. Free for academic, personal, and commercial use. 🎓

---

**Developed with ❤️ by [Ahnaf Nafee](https://github.com/ahnafnafee)**
