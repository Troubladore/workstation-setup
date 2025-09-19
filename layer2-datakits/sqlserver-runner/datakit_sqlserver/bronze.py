import hashlib
import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine


def run_bronze_table(table: str, source_url: str, target_url: str, batch_id: str) -> int:
    src = create_engine(source_url)
    tgt = create_engine(target_url)
    df = pd.read_sql(f"SELECT * FROM {table}", src)
    if df.empty:
        return 0
    df["br_load_time"] = datetime.now()
    df["br_source_table"] = table
    df["br_batch_id"] = batch_id
    df["br_is_current"] = True
    cols = [c for c in df.columns if not c.startswith("br_")]
    df["br_record_hash"] = (
        df[cols]
        .astype(str)
        .agg("|".join, axis=1)
        .map(lambda s: hashlib.md5(s.encode()).hexdigest())
    )
    df[f"br_{table}_key"] = [str(uuid.uuid4()) for _ in range(len(df))]
    df[cols] = df[cols].astype(str)
    df.to_sql(
        name=f"br_{table}",
        con=tgt,
        schema="staging",
        if_exists="replace",
        index=False,
        method="multi",
    )
    src.dispose()
    tgt.dispose()
    return len(df)
