# Astronomer Runtime for Airflow 3.0.6 (+astro.1)
FROM astrocrpublic.azurecr.io/runtime:3.0-10  # Latest Astro Runtime 3.0.10 with Airflow 3.0.6

# System deps you may want for providers, etc.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends     krb5-user curl jq   && rm -rf /var/lib/apt/lists/*
USER astro
