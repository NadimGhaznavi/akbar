"""Create configured MariaDB connections for Akbar services."""

import os

import pymysql
from pymysql.cursors import DictCursor

from constants.DDatabase import DDatabase


def connect():
    return pymysql.connect(
        host=os.getenv("AKBAR_DB_HOST", DDatabase.HOST),
        port=int(os.getenv("AKBAR_DB_PORT", str(DDatabase.PORT))),
        user=os.getenv("AKBAR_DB_USER", DDatabase.USERNAME),
        password=os.environ["AKBAR_DB_PASSWORD"],
        database=os.getenv("AKBAR_DB_NAME", DDatabase.DB_NAME),
        charset="utf8mb4",
        autocommit=True,
        cursorclass=DictCursor,
    )
