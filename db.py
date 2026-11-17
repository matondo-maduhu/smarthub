"""Muunganisho wa Neon (Postgres).

Tengeneza majedwali:  python db.py init
Jaribu muunganisho:   python db.py ping
"""
import os
import sys
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from config import Config

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# Kosa la "tayari ipo" (barua pepe, simu au jina la mtumiaji lililotumika)
IntegrityError = psycopg2.IntegrityError


def _dsn():
    if not Config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL haijawekwa kwenye .env")
    return Config.DATABASE_URL


@contextmanager
def get_conn():
    conn = psycopg2.connect(_dsn(), cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, params=None, one=False):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        if cur.description is None:
            return None
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows


def execute(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())


def init_db():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
    print("Majedwali yametengenezwa.")


def ping():
    row = query("SELECT 1 AS ok", one=True)
    return bool(row and row["ok"] == 1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        init_db()
    elif cmd == "ping":
        print("Neon inafanya kazi" if ping() else "Imeshindwa")
    else:
        print("Tumia: python db.py init  |  python db.py ping")
