FROM astrocrpublic.azurecr.io/runtime:3.0-10  # Latest Astro Runtime 3.0.10 with Airflow 3.0.6
USER root
RUN apt-get update && apt-get install -y --no-install-recommends krb5-user && rm -rf /var/lib/apt/lists/*
USER astro
