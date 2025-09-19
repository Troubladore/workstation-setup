# Production

- Two enclaves (standard, high) deployed to K8s clusters.
- Each contract receives isolated Airflow deployment + schema namespaces.
- Routing via corporate domain: `airflow-dev.customer.myco.com`, etc.
- dbt packages pinned; dimensions built first, then facts.
- Monitoring + lineage layered in.
