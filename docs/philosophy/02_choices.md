# Key Architectural Choices

- **Astronomer Runtime**: Opinionated packaging of Airflow, avoids bespoke infra.
- **DockerOperator locally, KPO in prod**: Achieves fidelity without overburdening devs with Kubernetes.
- **Traefik + .localhost**: Secure routing without hosts file hacks or lvh.me.
- **dbt for Silver/Gold**: SQL-first where possible, approachable by a wide audience.
- **Conformed Dimensions Package**: Prevents drift across fact topics.
