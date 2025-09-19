import typer

from .job import run_local_bronze

app = typer.Typer()


@app.command()
def ingest(
    table: str,
    source_url: str = typer.Option(..., help="jdbc:postgresql://host:port/db"),
    target_url: str = typer.Option(..., help="jdbc:postgresql://host:port/db"),
    batch_id: str = typer.Option(...),
):
    rows = run_local_bronze(table, source_url, target_url, batch_id)
    print({"table": table, "rows_processed": rows})
