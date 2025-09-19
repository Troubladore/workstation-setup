# datakit-sqlserver-runner

Runner image and Python package for SQL Server bronze ingestion using **SQLModel + SQLAlchemy 2.x**.

- No Airflow dependency.
- CLI entrypoint: `datakit-sqlsrv --help`
- Works with Kerberos by mounting a ccache at `/ccache` (set `KRB5CCNAME=/ccache/krb5cc`).

> Note: This template uses `pyodbc` with FreeTDS packages for dev. In prod you may switch to Microsoft ODBC Driver.
