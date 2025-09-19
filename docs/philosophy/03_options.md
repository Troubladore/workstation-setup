# Options Considered

- **Secrets**: Delinea vs Azure Key Vault → we standardized on Azure for tighter cloud integration.
- **SQLModel in Silver/Gold**: Chosen to limit its scope to Bronze; dbt took over for analytics layers.
- **Kerberos Auth**: Sidecar approach selected for parity between dev/prod, rather than ticket forwarding hacks.
- **Subdomains**: env-centric naming (`airflow-dev.customer.localhost`) vs enclaves (`low/high`). We went env-centric to simplify developer experience.
