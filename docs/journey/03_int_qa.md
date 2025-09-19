# Integration & QA

- Separate cluster(s) for integration testing and QA validation.
- Use same Astronomer + dbt setup, different namespaces.
- Contract-by-contract isolation enforced by Kubernetes namespace + network policies.
- Automated regression tests run here.
