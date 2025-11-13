"""Main CLI interface for Laravel RAG system."""

# Must be first import to patch ChromaDB telemetry
from src.utils.chromadb_fix import disable_chromadb_telemetry

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.config import settings
from src.extraction.docs_fetcher import DocsFetcher
from src.extraction.markdown_parser import MarkdownParser
from src.indexing.embeddings import OllamaEmbeddings
from src.indexing.vector_store import VectorStore
from src.retrieval.rag_chain import RAGChain
from src.utils.logger import app_logger as logger

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Laravel Documentation RAG System - CLI Interface."""
    pass


@cli.command()
@click.option(
    "--version",
    default=settings.laravel_version,
    help="Laravel version to extract",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-extraction even if docs exist",
)
def extract(version: str, force: bool):
    """Extract Laravel documentation from GitHub."""
    console.print(f"[bold blue]Extracting Laravel v{version} documentation...[/bold blue]")

    try:
        fetcher = DocsFetcher(version=version)
        docs_dir = fetcher.fetch_docs(force=force)

        # Get stats
        markdown_files = fetcher.get_markdown_files()

        console.print(f"[green]Successfully extracted {len(markdown_files)} Markdown files[/green]")
        console.print(f"[green]Location: {docs_dir}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Extraction failed: {e}")
        raise click.Abort()


@cli.command()
@click.option(
    "--version",
    default=settings.laravel_version,
    help="Laravel version to index",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-indexing (clears existing data for version)",
)
@click.option(
    "--batch-size",
    default=None,
    type=int,
    help=f"Batch size for embedding generation (default: {settings.batch_size})",
)
@click.option(
    "--parallel/--no-parallel",
    default=True,
    help="Enable/disable parallel processing (default: enabled)",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help=f"Number of parallel workers (default: {settings.max_workers})",
)
@click.option(
    "--chunk-strategy",
    type=click.Choice(["anchor", "adaptive"]),
    default=None,
    help=f"Chunking strategy (default: {settings.chunk_strategy})",
)
@click.option(
    "--max-chunk-size",
    default=None,
    type=int,
    help=f"Maximum chunk size in characters (default: {settings.max_chunk_size})",
)
@click.option(
    "--chunk-overlap",
    default=None,
    type=int,
    help=f"Chunk overlap in characters (default: {settings.chunk_overlap})",
)
def index(
    version: str,
    force: bool,
    batch_size: int,
    parallel: bool,
    workers: int,
    chunk_strategy: str,
    max_chunk_size: int,
    chunk_overlap: int,
):
    """Index Laravel documentation into vector store with parallel processing."""
    batch_size = batch_size or settings.batch_size
    workers = workers or settings.max_workers
    chunk_strategy = chunk_strategy or settings.chunk_strategy
    max_chunk_size = max_chunk_size or settings.max_chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    console.print(f"[bold blue]Indexing Laravel v{version} documentation...[/bold blue]")
    console.print(f"[cyan]Chunk strategy: {chunk_strategy}[/cyan]")
    if chunk_strategy == "adaptive":
        console.print(f"[cyan]Max chunk size: {max_chunk_size} chars, Overlap: {chunk_overlap} chars[/cyan]")
    if parallel:
        console.print(f"[cyan]Parallel processing: enabled ({workers} workers)[/cyan]")
    else:
        console.print(f"[cyan]Parallel processing: disabled (sequential)[/cyan]")

    try:
        # Check if models are available
        console.print("[yellow]Checking model availability...[/yellow]")

        embeddings = OllamaEmbeddings()
        if not embeddings.check_model_availability():
            console.print(f"[yellow]Pulling embedding model: {settings.embedding_model}[/yellow]")
            embeddings.pull_model()

        # Initialize vector store
        vector_store = VectorStore(embeddings=embeddings)

        # Clear existing data if force
        if force:
            console.print(f"[yellow]Clearing existing data for version {version}...[/yellow]")
            vector_store.clear_version(version)

        # Parse documentation
        console.print("[yellow]Parsing documentation files...[/yellow]")
        fetcher = DocsFetcher(version=version)
        docs_dir = fetcher.version_dir

        if not docs_dir.exists():
            console.print("[red]Documentation not found. Run 'extract' first.[/red]")
            raise click.Abort()

        parser = MarkdownParser(
            version=version,
            chunk_strategy=chunk_strategy,
            max_chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )
        sections = parser.parse_directory(docs_dir)

        console.print(f"[green]Parsed {len(sections)} sections[/green]")

        # Index sections with parallel processing
        console.print("[yellow]Generating embeddings and indexing...[/yellow]")
        console.print(f"[dim]Batch size: {batch_size}, Workers: {workers if parallel else 'sequential'}[/dim]")

        import time
        start_time = time.time()

        with console.status("[bold green]Indexing in progress..."):
            added_count = vector_store.add_sections(
                sections,
                batch_size=batch_size,
                parallel=parallel,
                max_workers=workers if parallel else None
            )

        elapsed = time.time() - start_time
        rate = added_count / elapsed if elapsed > 0 else 0

        console.print(f"[green]Successfully indexed {added_count} sections in {elapsed:.1f}s[/green]")
        console.print(f"[cyan]Indexing rate: {rate:.1f} sections/second[/cyan]")

        # Show stats
        stats = vector_store.get_stats()
        console.print(f"[green]Total documents in store: {stats['total_documents']}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Indexing failed: {e}")
        raise click.Abort()


@cli.command()
@click.argument("question")
@click.option(
    "--version",
    help="Filter by Laravel version",
)
@click.option(
    "--top-k",
    default=settings.top_k,
    help="Number of relevant sections to retrieve",
)
@click.option(
    "--show-sources",
    is_flag=True,
    help="Show source documents",
)
@click.option(
    "--temperature",
    default=0.7,
    type=float,
    help="LLM temperature (0.0-1.0)",
)
def query(question: str, version: str, top_k: int, show_sources: bool, temperature: float):
    """Query Laravel documentation."""
    console.print(Panel(f"[bold cyan]Question:[/bold cyan] {question}"))

    try:
        # Initialize RAG chain
        rag_chain = RAGChain(top_k=top_k)

        # Check LLM availability
        if not rag_chain.check_llm_availability():
            console.print(f"[yellow]Pulling LLM model: {settings.llm_model}[/yellow]")
            rag_chain.pull_model()

        # Execute query
        with console.status("[bold green]Searching and generating response..."):
            response = rag_chain.query(
                question=question,
                version_filter=version,
                include_sources=show_sources,
                temperature=temperature,
            )

        # Display answer
        console.print("\n[bold green]Answer:[/bold green]")
        console.print(Panel(Markdown(response["answer"])))

        # Display sources if requested
        if show_sources and "sources" in response:
            console.print("\n[bold blue]Sources:[/bold blue]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("File", style="cyan")
            table.add_column("Section", style="green")
            table.add_column("Version", style="yellow")
            table.add_column("Distance", style="red")

            for source in response["sources"]:
                table.add_row(
                    source["file"],
                    source["section"],
                    source["version"],
                    f"{source['distance']:.4f}",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Query failed: {e}")
        raise click.Abort()


@cli.command()
@click.option(
    "--version",
    help="Filter by version",
)
def stats(version: str):
    """Show vector store statistics."""
    try:
        vector_store = VectorStore()
        stats_data = vector_store.get_stats()

        console.print("[bold blue]Vector Store Statistics[/bold blue]")
        console.print(f"Collection: {stats_data['collection_name']}")
        console.print(f"Persist Directory: {stats_data['persist_dir']}")
        console.print(f"Total Documents: {stats_data['total_documents']}")

        if stats_data.get("versions"):
            console.print("\n[bold green]Version Distribution:[/bold green]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Version", style="cyan")
            table.add_column("Document Count", style="green")

            for ver, count in stats_data["versions"].items():
                table.add_row(ver, str(count))

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Stats retrieval failed: {e}")


@cli.command()
def interactive():
    """Start interactive query mode."""
    console.print("[bold green]Laravel RAG - Interactive Mode[/bold green]")
    console.print("Type 'exit' or 'quit' to stop\n")

    try:
        rag_chain = RAGChain()

        # Check models
        if not rag_chain.check_llm_availability():
            console.print(f"[yellow]Pulling LLM model: {settings.llm_model}[/yellow]")
            rag_chain.pull_model()

        while True:
            question = console.input("[bold cyan]Question:[/bold cyan] ")

            if question.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if not question.strip():
                continue

            try:
                with console.status("[bold green]Thinking..."):
                    response = rag_chain.query(
                        question=question,
                        include_sources=False,
                    )

                console.print("\n[bold green]Answer:[/bold green]")
                console.print(Panel(Markdown(response["answer"])))
                console.print()

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]\n")
                continue

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Goodbye![/yellow]")


@cli.command()
@click.option("--version", help="Check specific version")
def check(version: str):
    """Check system status and model availability."""
    console.print("[bold blue]System Status Check[/bold blue]\n")

    # Check embeddings model
    console.print("[yellow]Checking embedding model...[/yellow]")
    embeddings = OllamaEmbeddings()
    if embeddings.check_model_availability():
        console.print(f"[green]✓ Embedding model ({settings.embedding_model}) is available[/green]")
    else:
        console.print(f"[red]✗ Embedding model ({settings.embedding_model}) not found[/red]")

    # Check LLM model
    console.print("[yellow]Checking LLM model...[/yellow]")
    rag_chain = RAGChain()
    if rag_chain.check_llm_availability():
        console.print(f"[green]✓ LLM model ({settings.llm_model}) is available[/green]")
    else:
        console.print(f"[red]✗ LLM model ({settings.llm_model}) not found[/red]")

    # Check vector store
    console.print("[yellow]Checking vector store...[/yellow]")
    vector_store = VectorStore()
    stats_data = vector_store.get_stats()
    console.print(f"[green]✓ Vector store has {stats_data['total_documents']} documents[/green]")

    # Check documentation
    if version:
        console.print(f"[yellow]Checking documentation for version {version}...[/yellow]")
        fetcher = DocsFetcher(version=version)
        if fetcher.version_dir.exists():
            files = fetcher.get_markdown_files()
            console.print(f"[green]✓ Documentation found: {len(files)} files[/green]")
        else:
            console.print(f"[red]✗ Documentation not found for version {version}[/red]")


if __name__ == "__main__":
    cli()
