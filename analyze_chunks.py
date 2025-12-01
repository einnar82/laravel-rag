#!/usr/bin/env python3
"""Analyze and compare different chunking strategies for Laravel documentation.

This utility helps optimize chunk size parameters by showing statistics
and allowing comparison between 'anchor' and 'adaptive' strategies.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config import settings
from src.extraction.docs_fetcher import DocsFetcher
from src.extraction.markdown_parser import MarkdownParser

console = Console()


def analyze_chunking(
    version: str = "12",
    chunk_strategy: str = "adaptive",
    max_chunk_size: int = 2000,
    min_chunk_size: int = 200,
    chunk_overlap: int = 200,
):
    """Analyze chunking for a specific configuration.

    Args:
        version: Laravel version to analyze
        chunk_strategy: 'anchor' or 'adaptive'
        max_chunk_size: Maximum characters per chunk
        min_chunk_size: Minimum characters per chunk
        chunk_overlap: Overlap between chunks
    """
    console.print(f"[bold blue]Analyzing {chunk_strategy} chunking strategy[/bold blue]")
    console.print(f"[cyan]Version: {version}[/cyan]")

    if chunk_strategy == "adaptive":
        console.print(f"[cyan]Max chunk size: {max_chunk_size} chars[/cyan]")
        console.print(f"[cyan]Min chunk size: {min_chunk_size} chars[/cyan]")
        console.print(f"[cyan]Chunk overlap: {chunk_overlap} chars[/cyan]")

    console.print()

    # Check if docs exist
    fetcher = DocsFetcher(version=version)
    docs_dir = fetcher.version_dir

    if not docs_dir.exists():
        console.print("[red]Documentation not found. Run 'make extract' first.[/red]")
        sys.exit(1)

    # Parse with specified strategy
    parser = MarkdownParser(
        version=version,
        chunk_strategy=chunk_strategy,
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
        chunk_overlap=chunk_overlap,
    )

    sections = parser.parse_directory(docs_dir)

    # Calculate statistics
    chunk_sizes = [len(section.content) for section in sections]
    total_chunks = len(sections)
    total_chars = sum(chunk_sizes)
    avg_size = total_chars / total_chunks if total_chunks > 0 else 0
    min_size = min(chunk_sizes) if chunk_sizes else 0
    max_size = max(chunk_sizes) if chunk_sizes else 0

    # Count multi-part sections (only in adaptive mode)
    multi_part_sections = set()
    for section in sections:
        if "Part" in section.section:
            # Extract base section name
            base_name = section.section.split(" (Part")[0]
            multi_part_sections.add(base_name)

    # Display statistics
    table = Table(title="Chunking Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total chunks", str(total_chunks))
    table.add_row("Total characters", f"{total_chars:,}")
    table.add_row("Average chunk size", f"{avg_size:.0f} chars")
    table.add_row("Minimum chunk size", f"{min_size:,} chars")
    table.add_row("Maximum chunk size", f"{max_size:,} chars")

    if chunk_strategy == "adaptive":
        table.add_row("Sections split into parts", str(len(multi_part_sections)))

    console.print(table)

    # Show size distribution
    console.print("\n[bold blue]Size Distribution[/bold blue]")
    size_ranges = [
        (0, 500, "0-500 chars"),
        (500, 1000, "500-1K chars"),
        (1000, 2000, "1K-2K chars"),
        (2000, 3000, "2K-3K chars"),
        (3000, 5000, "3K-5K chars"),
        (5000, float('inf'), "5K+ chars"),
    ]

    dist_table = Table(show_header=True, header_style="bold magenta")
    dist_table.add_column("Size Range", style="cyan")
    dist_table.add_column("Count", style="green")
    dist_table.add_column("Percentage", style="yellow")

    for min_range, max_range, label in size_ranges:
        count = sum(1 for size in chunk_sizes if min_range <= size < max_range)
        percentage = (count / total_chunks * 100) if total_chunks > 0 else 0
        dist_table.add_row(label, str(count), f"{percentage:.1f}%")

    console.print(dist_table)

    # Show examples of largest chunks
    console.print("\n[bold blue]Top 5 Largest Chunks[/bold blue]")
    sorted_sections = sorted(sections, key=lambda s: len(s.content), reverse=True)[:5]

    examples_table = Table(show_header=True, header_style="bold magenta")
    examples_table.add_column("File", style="cyan")
    examples_table.add_column("Section", style="green")
    examples_table.add_column("Size", style="yellow")

    for section in sorted_sections:
        examples_table.add_row(
            section.file,
            section.section[:50] + "..." if len(section.section) > 50 else section.section,
            f"{len(section.content):,} chars"
        )

    console.print(examples_table)

    return sections


def compare_strategies(version: str = "12"):
    """Compare anchor and adaptive strategies side by side.

    Args:
        version: Laravel version to analyze
    """
    console.print(Panel("[bold green]Comparing Chunking Strategies[/bold green]"))

    # Analyze anchor strategy
    console.print("\n[bold yellow]═══ ANCHOR STRATEGY (Original) ═══[/bold yellow]\n")
    anchor_sections = analyze_chunking(version=version, chunk_strategy="anchor")

    console.print("\n\n")

    # Analyze adaptive strategy
    console.print("[bold yellow]═══ ADAPTIVE STRATEGY (Smart Splitting) ═══[/bold yellow]\n")
    adaptive_sections = analyze_chunking(
        version=version,
        chunk_strategy="adaptive",
        max_chunk_size=settings.max_chunk_size,
        min_chunk_size=settings.min_chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Summary comparison
    console.print("\n\n")
    summary = Table(title="Strategy Comparison", show_header=True, header_style="bold magenta")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Anchor", style="yellow")
    summary.add_column("Adaptive", style="green")
    summary.add_column("Difference", style="red")

    anchor_count = len(anchor_sections)
    adaptive_count = len(adaptive_sections)
    diff_count = adaptive_count - anchor_count
    diff_pct = (diff_count / anchor_count * 100) if anchor_count > 0 else 0

    summary.add_row(
        "Total chunks",
        str(anchor_count),
        str(adaptive_count),
        f"+{diff_count} ({diff_pct:+.1f}%)"
    )

    anchor_avg = sum(len(s.content) for s in anchor_sections) / len(anchor_sections)
    adaptive_avg = sum(len(s.content) for s in adaptive_sections) / len(adaptive_sections)
    avg_diff = adaptive_avg - anchor_avg
    avg_diff_pct = (avg_diff / anchor_avg * 100) if anchor_avg > 0 else 0

    summary.add_row(
        "Average chunk size",
        f"{anchor_avg:.0f} chars",
        f"{adaptive_avg:.0f} chars",
        f"{avg_diff:+.0f} ({avg_diff_pct:+.1f}%)"
    )

    console.print(summary)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze chunking strategies")
    parser.add_argument("--version", default="12", help="Laravel version")
    parser.add_argument(
        "--strategy",
        choices=["anchor", "adaptive", "compare"],
        default="compare",
        help="Strategy to analyze or 'compare' for both"
    )
    parser.add_argument("--max-chunk-size", type=int, default=2000, help="Max chunk size")
    parser.add_argument("--min-chunk-size", type=int, default=200, help="Min chunk size")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap")

    args = parser.parse_args()

    if args.strategy == "compare":
        compare_strategies(version=args.version)
    else:
        analyze_chunking(
            version=args.version,
            chunk_strategy=args.strategy,
            max_chunk_size=args.max_chunk_size,
            min_chunk_size=args.min_chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
