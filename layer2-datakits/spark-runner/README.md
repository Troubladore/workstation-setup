# datakit-spark-runner

Runner image and Python package for **PySpark (local mode)** bronze ingestion.
- No Airflow dependency.
- CLI: `datakit-spark`.
- Starts a local SparkSession by default (no K8s required).

> Pin your desired PySpark version via build arg `PIP_PYSPARK`.
