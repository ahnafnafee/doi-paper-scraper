"""CLI entry point — paper-scrape command."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from academic_paper_api.doi_resolver import extract_doi, resolve_doi
from academic_paper_api.markdown_builder import save_paper
from academic_paper_api.scrapers import get_scraper

console = Console()


@click.command()
@click.argument("doi_input")
@click.option(
    "--output-dir", "-o",
    default="./output",
    type=click.Path(),
    help="Directory to save the output Markdown and images.",
)
@click.option(
    "--cookies",
    default=None,
    type=click.Path(exists=True),
    help="Path to a JSON cookies file for authenticated access (e.g. institutional login).",
)
def main(doi_input: str, output_dir: str, cookies: str | None) -> None:
    """Scrape an academic paper by DOI and reconstruct it as Markdown.

    DOI_INPUT can be any of:

    \b
      - A plain DOI:        10.1145/3746059.3747603
      - A doi.org URL:      https://doi.org/10.1145/3746059.3747603
      - A publisher URL:    https://dl.acm.org/doi/10.1145/3746059.3747603
      - Any URL or string containing a DOI
    """
    out = Path(output_dir)

    # ── Step 1: Extract & resolve DOI ──────────────────────────────
    with console.status("[bold cyan]Resolving DOI…"):
        try:
            doi = extract_doi(doi_input)
            console.print(f"  DOI extracted: [green]{doi}[/green]")

            resolved = resolve_doi(doi_input)
            console.print(f"  Publisher:     [green]{resolved.publisher.upper()}[/green]")
            console.print(f"  URL:           [dim]{resolved.url}[/dim]")
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise SystemExit(1)

    # ── Step 2: Select scraper ────────────────────────────────────
    try:
        scraper = get_scraper(resolved.publisher)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    # ── Step 3: Scrape ────────────────────────────────────────────
    console.print()
    console.print(
        Panel(f"Scraping with [bold]{scraper.publisher_name.upper()}[/bold] scraper…",
              style="cyan")
    )

    try:
        paper = scraper.scrape(
            url=resolved.url,
            doi=resolved.doi,
            output_dir=out,
            cookies_file=cookies,
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        console.print(f"[bold red]Scraping failed:[/bold red] {exc}")
        raise SystemExit(1)

    # ── Step 4: Save Markdown ─────────────────────────────────────
    md_path = save_paper(paper, out)

    console.print()
    console.print(Panel.fit(
        f"[bold green]✓ Done![/bold green]\n\n"
        f"  Title:    {paper.title}\n"
        f"  Authors:  {', '.join(paper.authors[:5])}{'…' if len(paper.authors) > 5 else ''}\n"
        f"  Sections: {len(paper.sections)}\n"
        f"  Output:   [link=file://{md_path.resolve()}]{md_path}[/link]",
        title="Paper Scraped",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
