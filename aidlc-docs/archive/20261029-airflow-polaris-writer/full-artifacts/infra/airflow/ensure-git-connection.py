#!/usr/bin/env python3
"""Ensure the public Git Bundle source has a credential-free Airflow connection."""

from airflow.models import Connection
from airflow.utils.session import create_session

CONNECTION_ID = "lakehouse_git"

with create_session() as session:
    current = session.query(Connection).filter(Connection.conn_id == CONNECTION_ID).one_or_none()
    if current is None:
        session.add(Connection(conn_id=CONNECTION_ID, conn_type="git", host="github.com"))
        print("Airflow Git Bundle connection was created without embedded credentials.")
    elif current.conn_type != "git":
        raise SystemExit("Airflow lakehouse_git connection exists with an unexpected type.")
    else:
        print("Airflow Git Bundle connection is ready.")
