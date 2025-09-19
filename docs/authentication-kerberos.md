# Authentication & Security Guide

A comprehensive guide to implementing authentication, security, and Kerberos integration in our Astronomer Airflow data platform.

## 🎯 Security Architecture Overview

Our platform implements defense-in-depth with multiple security layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    External Access Layer                     │
│            OAuth2 / SAML / Corporate SSO                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Airflow Web Layer                         │
│            RBAC / JWT Tokens / Session Management            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Task Execution Layer                         │
│         Kerberos / Service Accounts / API Keys              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Data Access Layer                         │
│       Database Auth / Row-Level Security / Encryption        │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Kerberos Authentication

### **Understanding Kerberos in Our Platform**

Kerberos provides secure authentication for accessing enterprise systems like SQL Server, Hadoop, and other kerberized services.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   KDC/AD     │◄───►│   Airflow    │────►│  SQL Server  │
│              │     │   Worker     │     │              │
│  1. TGT      │     │  2. Use TGT  │     │  3. Access   │
│  Request     │     │  for Service │     │  with ticket │
└──────────────┘     └──────────────┘     └──────────────┘
```

### **Kerberos Implementation**

#### **1. Kerberos Sidecar Pattern**

```yaml
# layer1-platform-krb-renewer/Dockerfile
FROM alpine:3.18

# Install Kerberos client
RUN apk add --no-cache \
    krb5 \
    krb5-libs \
    bash \
    coreutils

# Copy configuration
COPY krb5.conf /etc/krb5.conf
COPY renew.sh /usr/local/bin/renew.sh

# Create cache directory
RUN mkdir -p /tmp/krb5cc && chmod 777 /tmp/krb5cc

ENTRYPOINT ["/usr/local/bin/renew.sh"]
```

```bash
#!/bin/bash
# layer1-platform-krb-renewer/renew.sh

set -e

# Configuration from environment
PRINCIPAL="${KRB_PRINCIPAL}"
KEYTAB="${KRB_KEYTAB:-/keytab/service.keytab}"
CACHE="${KRB5CCNAME:-FILE:/tmp/krb5cc/krb5cc}"
RENEWAL_INTERVAL="${KRB_RENEWAL_INTERVAL:-3600}"

echo "Starting Kerberos ticket renewal for ${PRINCIPAL}"

# Initial authentication
kinit -kt "${KEYTAB}" "${PRINCIPAL}"

# Renewal loop
while true; do
    echo "$(date): Renewing Kerberos ticket"

    # Check ticket status
    if klist -s; then
        echo "Current ticket valid"
        # Renew ticket
        kinit -R || kinit -kt "${KEYTAB}" "${PRINCIPAL}"
    else
        echo "Ticket expired, re-authenticating"
        kinit -kt "${KEYTAB}" "${PRINCIPAL}"
    fi

    # Copy to shared location
    cp "${KRB5CCNAME#FILE:}" /tmp/krb5cc/krb5cc
    chmod 644 /tmp/krb5cc/krb5cc

    # Sleep before next renewal
    sleep "${RENEWAL_INTERVAL}"
done
```

#### **2. Kerberos Configuration**

```ini
# /etc/krb5.conf
[libdefaults]
    default_realm = COMPANY.COM
    dns_lookup_realm = false
    dns_lookup_kdc = false
    ticket_lifetime = 24h
    renew_lifetime = 7d
    forwardable = true
    rdns = false
    pkinit_anchors = FILE:/etc/pki/tls/certs/ca-bundle.crt
    default_ccache_name = FILE:/tmp/krb5cc/krb5cc_%{uid}

[realms]
    COMPANY.COM = {
        kdc = kdc1.company.com
        kdc = kdc2.company.com
        admin_server = kdc1.company.com
        default_domain = company.com
    }

    SUBSIDIARY.COM = {
        kdc = kdc.subsidiary.com
        admin_server = kdc.subsidiary.com
        default_domain = subsidiary.com
    }

[domain_realm]
    .company.com = COMPANY.COM
    company.com = COMPANY.COM
    .subsidiary.com = SUBSIDIARY.COM
    subsidiary.com = SUBSIDIARY.COM

[logging]
    default = FILE:/var/log/krb5libs.log
    kdc = FILE:/var/log/krb5kdc.log
    admin_server = FILE:/var/log/kadmind.log
```

#### **3. Docker Compose with Kerberos**

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  krb-renewer:
    image: registry.localhost/platform/krb-renewer:1.0.0
    container_name: krb-renewer
    environment:
      KRB_PRINCIPAL: ${KRB_PRINCIPAL:-svc_airflow@COMPANY.COM}
      KRB_KEYTAB: /keytab/service.keytab
      KRB5CCNAME: FILE:/tmp/krb5cc/krb5cc
    volumes:
      - ./keytabs:/keytab:ro
      - krb5cc:/tmp/krb5cc
    networks:
      - edge
    restart: unless-stopped

  scheduler:
    volumes:
      - krb5cc:/tmp/krb5cc:ro
    environment:
      KRB5CCNAME: FILE:/tmp/krb5cc/krb5cc

  worker:
    volumes:
      - krb5cc:/tmp/krb5cc:ro
    environment:
      KRB5CCNAME: FILE:/tmp/krb5cc/krb5cc

volumes:
  krb5cc:
    driver: local
```

#### **4. Using Kerberos in Datakits**

```python
# datakit_sqlserver/kerberos_extractor.py
import os
import subprocess
import pyodbc
import pandas as pd
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class KerberizedSQLServerExtractor:
    """SQL Server extraction with Kerberos authentication."""

    def __init__(self):
        self.server = os.getenv('SQL_SERVER_HOST')
        self.database = os.getenv('SQL_SERVER_DATABASE')
        self.krb5ccname = os.getenv('KRB5CCNAME', 'FILE:/tmp/krb5cc/krb5cc')

    def verify_kerberos_ticket(self):
        """Verify Kerberos ticket is valid."""
        try:
            result = subprocess.run(
                ['klist', '-s'],
                env={'KRB5CCNAME': self.krb5ccname},
                capture_output=True
            )
            if result.returncode != 0:
                raise Exception("No valid Kerberos ticket found")

            # Get ticket details
            result = subprocess.run(
                ['klist'],
                env={'KRB5CCNAME': self.krb5ccname},
                capture_output=True,
                text=True
            )
            logger.info(f"Kerberos ticket status:\n{result.stdout}")

        except Exception as e:
            logger.error(f"Kerberos verification failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get SQL Server connection using Kerberos."""
        self.verify_kerberos_ticket()

        # Connection string for Kerberos
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"Trusted_Connection=yes;"
            f"Authentication=ActiveDirectoryIntegrated;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )

        conn = None
        try:
            conn = pyodbc.connect(conn_str)
            logger.info(f"Connected to SQL Server: {self.server}/{self.database}")
            yield conn
        finally:
            if conn:
                conn.close()

    def extract_table(self, schema: str, table: str) -> pd.DataFrame:
        """Extract table using Kerberos authentication."""
        with self.get_connection() as conn:
            query = f"SELECT * FROM [{schema}].[{table}]"
            df = pd.read_sql(query, conn)
            logger.info(f"Extracted {len(df)} rows from {schema}.{table}")
            return df

# Dockerfile for Kerberos-enabled datakit
FROM python:3.11-slim

# Install SQL Server ODBC driver and Kerberos
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    krb5-user \
    libkrb5-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Kerberos configuration
COPY krb5.conf /etc/krb5.conf

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY datakit_sqlserver/ /app/datakit_sqlserver/

WORKDIR /app
ENTRYPOINT ["python", "-m", "datakit_sqlserver.kerberos_extractor"]
```

## 🔑 OAuth2 / SAML Authentication

### **OAuth2 Configuration for Airflow**

```python
# airflow_settings.yaml
auth:
  type: oauth
  oauth:
    provider: okta
    client_id: ${OAUTH_CLIENT_ID}
    client_secret: ${OAUTH_CLIENT_SECRET}
    base_url: https://company.okta.com
    redirect_uri: https://airflow.company.com/oauth-authorized
    authorize_url: /oauth2/v1/authorize
    access_token_url: /oauth2/v1/token
    user_info_url: /oauth2/v1/userinfo

# webserver_config.py
from flask_appbuilder.security.manager import AUTH_OAUTH
import os

AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Viewer"

OAUTH_PROVIDERS = [
    {
        'name': 'okta',
        'icon': 'fa-circle-o',
        'token_key': 'access_token',
        'remote_app': {
            'client_id': os.environ['OAUTH_CLIENT_ID'],
            'client_secret': os.environ['OAUTH_CLIENT_SECRET'],
            'server_metadata_url': f"{os.environ['OKTA_BASE_URL']}/.well-known/openid-configuration",
            'client_kwargs': {
                'scope': 'openid profile email groups'
            },
        }
    }
]

# Map OAuth groups to Airflow roles
AUTH_ROLES_MAPPING = {
    "airflow-admins": ["Admin"],
    "airflow-users": ["User"],
    "airflow-viewers": ["Viewer"],
    "data-engineers": ["User"],
    "data-scientists": ["Viewer"]
}

# Custom security manager
from airflow.www.security import AirflowSecurityManager

class CustomSecurityManager(AirflowSecurityManager):
    def oauth_user_info(self, provider, response=None):
        """Get user info from OAuth provider."""
        if provider == 'okta':
            me = self.appbuilder.sm.oauth_remotes[provider].get('userinfo')
            data = me.json()
            return {
                'username': data.get('email', '').split('@')[0],
                'email': data.get('email', ''),
                'first_name': data.get('given_name', ''),
                'last_name': data.get('family_name', ''),
                'role_keys': data.get('groups', [])
            }

CUSTOM_SECURITY_MANAGER = CustomSecurityManager
```

### **SAML Authentication Setup**

```python
# webserver_config.py for SAML
from flask_appbuilder.security.manager import AUTH_SAML
import os

AUTH_TYPE = AUTH_SAML
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Viewer"

# SAML Configuration
SAML_CONFIG = {
    'metadata': {
        'local': [os.path.join(os.path.dirname(__file__), 'saml', 'metadata.xml')]
    },
    'entityid': 'https://airflow.company.com/saml/metadata',
    'service': {
        'sp': {
            'name': 'Airflow',
            'endpoints': {
                'assertion_consumer_service': [
                    ('https://airflow.company.com/saml/sso', 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'),
                ],
                'single_logout_service': [
                    ('https://airflow.company.com/saml/slo', 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'),
                ],
            },
            'allow_unsolicited': True,
            'authn_requests_signed': False,
            'want_assertions_signed': True,
            'want_response_signed': False,
        }
    },
    'key_file': '/certs/saml.key',
    'cert_file': '/certs/saml.crt',
    'attribute_map_dir': '/saml/attributemaps',
}

# Attribute mapping
SAML_ATTRIBUTE_MAPPING = {
    'email': 'email',
    'username': 'uid',
    'first_name': 'givenName',
    'last_name': 'sn',
    'groups': 'memberOf'
}
```

## 🔒 API Key Management

### **Secure API Key Storage and Rotation**

```python
# api_key_manager.py
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hvac  # HashiCorp Vault client
import boto3  # AWS Secrets Manager
from cryptography.fernet import Fernet

class APIKeyManager:
    """Manage API keys securely across different backends."""

    def __init__(self, backend: str = 'vault'):
        self.backend = backend
        self._init_backend()

    def _init_backend(self):
        """Initialize the secrets backend."""
        if self.backend == 'vault':
            self.vault_client = hvac.Client(
                url=os.getenv('VAULT_ADDR'),
                token=os.getenv('VAULT_TOKEN')
            )
        elif self.backend == 'aws':
            self.secrets_client = boto3.client('secretsmanager')
        elif self.backend == 'kubernetes':
            # Use Kubernetes secrets
            pass
        elif self.backend == 'local':
            # Encrypted local storage
            self.fernet = Fernet(os.getenv('ENCRYPTION_KEY').encode())

    def generate_api_key(
        self,
        service_name: str,
        expiry_days: int = 90,
        rotation_days: int = 7
    ) -> Dict[str, Any]:
        """Generate a new API key with metadata."""

        # Generate secure random key
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Metadata
        metadata = {
            'service': service_name,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=expiry_days)).isoformat(),
            'rotate_after': (datetime.now() + timedelta(days=expiry_days - rotation_days)).isoformat(),
            'key_hash': key_hash,
            'version': 1,
            'active': True
        }

        # Store the key
        self._store_key(service_name, api_key, metadata)

        return {
            'api_key': api_key,
            'expires_at': metadata['expires_at'],
            'key_id': f"{service_name}-{metadata['version']}"
        }

    def _store_key(self, service_name: str, api_key: str, metadata: Dict[str, Any]):
        """Store API key in the backend."""

        if self.backend == 'vault':
            self.vault_client.write(
                f'secret/api-keys/{service_name}',
                api_key=api_key,
                **metadata
            )

        elif self.backend == 'aws':
            self.secrets_client.create_secret(
                Name=f'api-key/{service_name}',
                SecretString=json.dumps({
                    'api_key': api_key,
                    'metadata': metadata
                }),
                Tags=[
                    {'Key': 'Service', 'Value': service_name},
                    {'Key': 'Type', 'Value': 'api-key'}
                ]
            )

        elif self.backend == 'kubernetes':
            from kubernetes import client, config
            config.load_incluster_config()
            v1 = client.CoreV1Api()

            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=f'api-key-{service_name}',
                    labels={'type': 'api-key', 'service': service_name}
                ),
                string_data={
                    'api_key': api_key,
                    'metadata': json.dumps(metadata)
                }
            )
            v1.create_namespaced_secret(namespace='default', body=secret)

    def get_api_key(self, service_name: str) -> Optional[str]:
        """Retrieve API key for a service."""

        if self.backend == 'vault':
            response = self.vault_client.read(f'secret/api-keys/{service_name}')
            if response:
                return response['data']['api_key']

        elif self.backend == 'aws':
            try:
                response = self.secrets_client.get_secret_value(
                    SecretId=f'api-key/{service_name}'
                )
                data = json.loads(response['SecretString'])
                return data['api_key']
            except:
                return None

        return None

    def rotate_api_key(self, service_name: str) -> Dict[str, Any]:
        """Rotate API key for a service."""

        # Get current key metadata
        current_metadata = self._get_metadata(service_name)

        # Generate new key
        new_key = self.generate_api_key(
            service_name,
            expiry_days=90,
            rotation_days=7
        )

        # Mark old key for deletion
        if current_metadata:
            current_metadata['active'] = False
            current_metadata['rotated_at'] = datetime.now().isoformat()
            current_metadata['delete_after'] = (
                datetime.now() + timedelta(days=7)
            ).isoformat()

            # Store updated metadata
            self._update_metadata(service_name, current_metadata)

        # Log rotation
        self._log_rotation(service_name, current_metadata, new_key)

        return new_key

    def validate_api_key(self, service_name: str, provided_key: str) -> bool:
        """Validate an API key."""

        stored_key = self.get_api_key(service_name)
        if not stored_key:
            return False

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(stored_key, provided_key)

# Using in Airflow
from airflow.hooks.base import BaseHook
from airflow.models import Variable

class SecureAPIConnection:
    """Secure API connection with key rotation."""

    def __init__(self, conn_id: str):
        self.conn = BaseHook.get_connection(conn_id)
        self.key_manager = APIKeyManager()

    def get_headers(self) -> Dict[str, str]:
        """Get headers with current API key."""

        # Check if key needs rotation
        service_name = self.conn.conn_id
        metadata = self.key_manager._get_metadata(service_name)

        if metadata and datetime.fromisoformat(metadata['rotate_after']) <= datetime.now():
            # Rotate the key
            new_key_info = self.key_manager.rotate_api_key(service_name)
            Variable.set(
                f"api_key_{service_name}_rotation",
                json.dumps(new_key_info),
                serialize_json=True
            )

        # Get current key
        api_key = self.key_manager.get_api_key(service_name)

        return {
            'Authorization': f'Bearer {api_key}',
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
```

## 🛡️ Database Authentication Patterns

### **Connection Pool with Authentication**

```python
# db_auth_manager.py
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool
import psycopg2
import pyodbc
from typing import Optional
import os

class DatabaseAuthManager:
    """Manage database connections with various authentication methods."""

    @staticmethod
    def create_postgres_engine(
        auth_method: str = 'password',
        **kwargs
    ):
        """Create PostgreSQL engine with specified authentication."""

        if auth_method == 'password':
            url = (
                f"postgresql://{kwargs['user']}:{kwargs['password']}"
                f"@{kwargs['host']}:{kwargs.get('port', 5432)}"
                f"/{kwargs['database']}"
            )

        elif auth_method == 'ssl_cert':
            url = (
                f"postgresql://{kwargs['user']}"
                f"@{kwargs['host']}:{kwargs.get('port', 5432)}"
                f"/{kwargs['database']}"
            )
            connect_args = {
                'sslmode': 'require',
                'sslcert': kwargs['ssl_cert'],
                'sslkey': kwargs['ssl_key'],
                'sslrootcert': kwargs['ssl_ca']
            }
            return create_engine(url, connect_args=connect_args)

        elif auth_method == 'iam':
            # AWS IAM authentication
            import boto3
            rds = boto3.client('rds')
            token = rds.generate_db_auth_token(
                DBHostname=kwargs['host'],
                Port=kwargs.get('port', 5432),
                DBUsername=kwargs['user']
            )
            url = (
                f"postgresql://{kwargs['user']}:{token}"
                f"@{kwargs['host']}:{kwargs.get('port', 5432)}"
                f"/{kwargs['database']}"
            )

        return create_engine(
            url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True
        )

    @staticmethod
    def create_sqlserver_engine(
        auth_method: str = 'kerberos',
        **kwargs
    ):
        """Create SQL Server engine with specified authentication."""

        if auth_method == 'kerberos':
            conn_str = (
                f"mssql+pyodbc://@{kwargs['host']}"
                f"/{kwargs['database']}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
                f"&Trusted_Connection=yes"
                f"&Authentication=ActiveDirectoryIntegrated"
            )

        elif auth_method == 'sql_auth':
            conn_str = (
                f"mssql+pyodbc://{kwargs['user']}:{kwargs['password']}"
                f"@{kwargs['host']}"
                f"/{kwargs['database']}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
            )

        elif auth_method == 'azure_ad':
            # Azure AD authentication
            import struct
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            token = credential.get_token(
                "https://database.windows.net/.default"
            )

            # Create connection with token
            conn_str = (
                f"mssql+pyodbc://@{kwargs['host']}"
                f"/{kwargs['database']}"
                f"?driver=ODBC+Driver+17+for+SQL+Server"
            )

            engine = create_engine(conn_str)

            @event.listens_for(engine, "do_connect")
            def receive_do_connect(dialect, conn_rec, cargs, cparams):
                # Inject the token
                cparams['attrs'] = {
                    1256: struct.pack('<I', len(token.token)) + token.token.encode('utf-16-le')
                }

            return engine

        return create_engine(
            conn_str,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600
        )

# Usage in Airflow
from airflow.providers.postgres.hooks.postgres import PostgresHook

class SecurePostgresHook(PostgresHook):
    """PostgreSQL hook with enhanced authentication."""

    def get_sqlalchemy_engine(self, engine_kwargs=None):
        """Get engine with authentication method from connection extras."""

        conn = self.get_connection(self.postgres_conn_id)
        extras = conn.extra_dejson

        auth_method = extras.get('auth_method', 'password')
        auth_manager = DatabaseAuthManager()

        if auth_method == 'iam':
            return auth_manager.create_postgres_engine(
                auth_method='iam',
                host=conn.host,
                port=conn.port,
                database=conn.schema,
                user=conn.login
            )

        return super().get_sqlalchemy_engine(engine_kwargs)
```

## 🔐 Secrets Management

### **HashiCorp Vault Integration**

```python
# vault_backend.py
from airflow.secrets import BaseSecretsBackend
from airflow.models import Connection, Variable
import hvac
import json
from typing import Optional, Union

class VaultSecretsBackend(BaseSecretsBackend):
    """HashiCorp Vault backend for Airflow secrets."""

    def __init__(
        self,
        vault_url: str = None,
        auth_method: str = 'token',
        **kwargs
    ):
        super().__init__()
        self.vault_url = vault_url or os.getenv('VAULT_ADDR')
        self.auth_method = auth_method
        self.client = self._get_client()

    def _get_client(self) -> hvac.Client:
        """Get authenticated Vault client."""

        client = hvac.Client(url=self.vault_url)

        if self.auth_method == 'token':
            client.token = os.getenv('VAULT_TOKEN')

        elif self.auth_method == 'kubernetes':
            # Kubernetes authentication
            with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as f:
                jwt = f.read()

            client.auth.kubernetes.login(
                role='airflow',
                jwt=jwt
            )

        elif self.auth_method == 'aws':
            # AWS IAM authentication
            client.auth.aws.iam_login(
                role='airflow-role'
            )

        return client

    def get_connection(
        self,
        conn_id: str,
        **kwargs
    ) -> Optional[Connection]:
        """Get connection from Vault."""

        try:
            response = self.client.read(
                f'secret/airflow/connections/{conn_id}'
            )

            if response and 'data' in response:
                data = response['data']

                return Connection(
                    conn_id=conn_id,
                    conn_type=data.get('conn_type'),
                    host=data.get('host'),
                    schema=data.get('schema'),
                    login=data.get('login'),
                    password=data.get('password'),
                    port=data.get('port'),
                    extra=json.dumps(data.get('extra', {}))
                )
        except Exception as e:
            self.log.error(f"Error getting connection {conn_id}: {e}")

        return None

    def get_variable(
        self,
        key: str,
        **kwargs
    ) -> Optional[str]:
        """Get variable from Vault."""

        try:
            response = self.client.read(
                f'secret/airflow/variables/{key}'
            )

            if response and 'data' in response:
                return response['data'].get('value')
        except Exception as e:
            self.log.error(f"Error getting variable {key}: {e}")

        return None

    def get_config(
        self,
        key: str,
        **kwargs
    ) -> Optional[str]:
        """Get configuration from Vault."""

        try:
            response = self.client.read(
                f'secret/airflow/config/{key}'
            )

            if response and 'data' in response:
                return json.dumps(response['data'])
        except Exception as e:
            self.log.error(f"Error getting config {key}: {e}")

        return None

# Configure in airflow.cfg
# [secrets]
# backend = vault_backend.VaultSecretsBackend
# backend_kwargs = {"vault_url": "https://vault.company.com", "auth_method": "kubernetes"}
```

## 🚨 Security Best Practices

### **1. Credential Rotation Policy**

```python
# credential_rotation.py
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CredentialRotationPolicy:
    """Enforce credential rotation policies."""

    ROTATION_POLICIES = {
        'api_key': {'max_age_days': 90, 'warning_days': 7},
        'database_password': {'max_age_days': 180, 'warning_days': 14},
        'kerberos_keytab': {'max_age_days': 365, 'warning_days': 30},
        'oauth_client_secret': {'max_age_days': 365, 'warning_days': 30},
        'ssl_certificate': {'max_age_days': 365, 'warning_days': 60}
    }

    @classmethod
    def check_rotation_needed(
        cls,
        credential_type: str,
        created_date: datetime
    ) -> Dict[str, Any]:
        """Check if credential needs rotation."""

        policy = cls.ROTATION_POLICIES.get(credential_type, {})
        max_age = policy.get('max_age_days', 365)
        warning_days = policy.get('warning_days', 30)

        age_days = (datetime.now() - created_date).days
        expires_in = max_age - age_days

        return {
            'needs_rotation': expires_in <= 0,
            'warning': expires_in <= warning_days,
            'expires_in_days': expires_in,
            'policy': policy
        }

    @classmethod
    def rotate_credential(
        cls,
        credential_type: str,
        current_credential: str
    ) -> str:
        """Rotate a credential based on its type."""

        logger.info(f"Rotating {credential_type}")

        if credential_type == 'api_key':
            return cls._rotate_api_key(current_credential)
        elif credential_type == 'database_password':
            return cls._rotate_database_password(current_credential)
        elif credential_type == 'kerberos_keytab':
            return cls._rotate_keytab(current_credential)

        raise ValueError(f"Unknown credential type: {credential_type}")
```

### **2. Audit Logging**

```python
# security_audit.py
import json
from datetime import datetime
from typing import Dict, Any
import structlog

audit_logger = structlog.get_logger('security_audit')

class SecurityAuditLogger:
    """Log security-relevant events."""

    @staticmethod
    def log_authentication(
        user: str,
        method: str,
        success: bool,
        ip_address: str = None,
        details: Dict[str, Any] = None
    ):
        """Log authentication attempts."""

        audit_logger.info(
            'authentication',
            user=user,
            method=method,
            success=success,
            ip_address=ip_address,
            timestamp=datetime.now().isoformat(),
            details=details or {}
        )

    @staticmethod
    def log_authorization(
        user: str,
        resource: str,
        action: str,
        granted: bool,
        reason: str = None
    ):
        """Log authorization decisions."""

        audit_logger.info(
            'authorization',
            user=user,
            resource=resource,
            action=action,
            granted=granted,
            reason=reason,
            timestamp=datetime.now().isoformat()
        )

    @staticmethod
    def log_data_access(
        user: str,
        database: str,
        table: str,
        operation: str,
        row_count: int = None,
        query: str = None
    ):
        """Log data access events."""

        audit_logger.info(
            'data_access',
            user=user,
            database=database,
            table=table,
            operation=operation,
            row_count=row_count,
            query_hash=hashlib.sha256(query.encode()).hexdigest() if query else None,
            timestamp=datetime.now().isoformat()
        )

    @staticmethod
    def log_credential_rotation(
        credential_type: str,
        service: str,
        old_credential_hash: str,
        new_credential_hash: str,
        rotated_by: str
    ):
        """Log credential rotation events."""

        audit_logger.info(
            'credential_rotation',
            credential_type=credential_type,
            service=service,
            old_credential_hash=old_credential_hash,
            new_credential_hash=new_credential_hash,
            rotated_by=rotated_by,
            timestamp=datetime.now().isoformat()
        )
```

## 🔗 Related Documentation

- [Container Orchestration](container-orchestration.md) - Security in containers
- [Multi-Tenant Setup](multi-tenant-setup.md) - Tenant isolation
- [Troubleshooting Guide](troubleshooting.md) - Security issue resolution
- [Monitoring & Observability](monitoring-observability.md) - Security monitoring

---

*Security is not a feature, it's a requirement. Always follow the principle of least privilege.*