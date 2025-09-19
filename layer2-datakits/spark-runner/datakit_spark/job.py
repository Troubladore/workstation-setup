from pyspark.sql import SparkSession, functions as F


def run_local_bronze(table: str, source_url: str, target_url: str, batch_id: str) -> int:
    spark = (
        SparkSession.builder.appName(f"bronze_{table}")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    df = spark.read.format("jdbc").option("url", source_url).option("dbtable", table).load()
    cols = [c for c in df.columns if not c.startswith("br_")]
    df = (
        df.select([F.col(c).cast("string").alias(c) for c in df.columns])
        .withColumn("br_load_time", F.current_timestamp())
        .withColumn("br_source_table", F.lit(table))
        .withColumn("br_batch_id", F.lit(batch_id))
        .withColumn("br_is_current", F.lit(True))
    )
    df = df.withColumn("br_record_hash", F.md5(F.concat_ws("|", *[F.col(c) for c in cols])))
    (
        df.write.format("jdbc")
        .option("url", target_url)
        .option("dbtable", f"staging.br_{table}")
        .mode("overwrite")
        .save()
    )
    n = df.count()
    spark.stop()
    return n
