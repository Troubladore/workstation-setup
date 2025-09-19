import typer

from .bronze import run_bronze_table

app = typer.Typer()


@app.command()
def ingest(
    table: str,
    source_url: str = typer.Option(..., help="postgresql+psycopg://user:pass@host:port/db"),
    target_url: str = typer.Option(..., help="postgresql+psycopg://..."),
    batch_id: str = typer.Option(...),
):
    rows = run_bronze_table(table, source_url, target_url, batch_id)
    print({"table": table, "rows_processed": rows})
