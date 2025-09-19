import os

import typer

from .bronze import run_bronze_table

app = typer.Typer()


@app.command()
def ingest(
    table: str,
    source_url: str = typer.Option(
        ..., help="SQLAlchemy URL for source (e.g., mssql+pyodbc://...)"
    ),
    target_url: str = typer.Option(..., help="SQLAlchemy URL for target"),
    batch_id: str = typer.Option(...),
):
    if "KRB5CCNAME" in os.environ:
        print(f"Using KRB5CCNAME={os.environ['KRB5CCNAME']}")
    rows = run_bronze_table(table, source_url, target_url, batch_id)
    print({"table": table, "rows_processed": rows})
