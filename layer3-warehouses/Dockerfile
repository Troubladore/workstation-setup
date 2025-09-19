FROM astrocrpublic.azurecr.io/runtime:3.0-10
USER root
RUN apt-get update && apt-get install -y --no-install-recommends krb5-user && rm -rf /var/lib/apt/lists/*
USER astro
