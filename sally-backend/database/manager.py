"""
Database Manager - Supports multiple database types
"""

from typing import Optional, Dict, Any, List
import os

# PostgreSQL (optional - used only if installed)
try:
    import psycopg2
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# MySQL (optional)
try:
    import pymysql
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# SQLite (always available in Python)
try:
    import aiosqlite
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

# MongoDB (optional)
try:
    from pymongo import MongoClient
    import motor.motor_asyncio
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# Oracle (optional)
try:
    import cx_Oracle
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False


class DatabaseManager:
    """
    Unified database manager supporting Postgres, MySQL, SQLite, Oracle, MongoDB
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.db = None

    async def connect(self):
        """Connect to database based on type"""

        db_type = self.config.get("type", "").lower()

        if db_type in ("postgres", "postgresql"):
            if not POSTGRES_AVAILABLE:
                raise ImportError("PostgreSQL driver not installed")
            return await self._connect_postgres()

        elif db_type == "mysql":
            if not MYSQL_AVAILABLE:
                raise ImportError(
                    "MySQL driver not installed. Add 'pymysql' and 'aiomysql' to requirements.txt"
                )
            return await self._connect_mysql()

        elif db_type == "sqlite":
            if not SQLITE_AVAILABLE:
                raise ImportError("SQLite driver not installed. Add 'aiosqlite' to requirements.txt")
            return await self._connect_sqlite()

        elif db_type == "mongodb":
            if not MONGODB_AVAILABLE:
                raise ImportError("MongoDB driver not installed. Add 'pymongo' + 'motor' to requirements.txt")
            return await self._connect_mongodb()

        elif db_type == "oracle":
            if not ORACLE_AVAILABLE:
                raise ImportError("Oracle driver not installed. Add 'cx-Oracle' to requirements.txt")
            return await self._connect_oracle()

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    # -----------------------------
    # Database-specific connectors
    # -----------------------------

    async def _connect_postgres(self):
        self.connection = await asyncpg.create_pool(
            host=self.config["host"],
            port=self.config.get("port", 5432),
            database=self.config["database"],
            user=self.config["user"],
            password=self.config["password"],
        )
        return True

    async def _connect_mysql(self):
        self.connection = await aiomysql.create_pool(
            host=self.config["host"],
            port=self.config.get("port", 3306),
            db=self.config["database"],
            user=self.config["user"],
            password=self.config["password"],
        )
        return True

    async def _connect_sqlite(self):
        self.connection = await aiosqlite.connect(self.config["database"])
        return True

    async def _connect_mongodb(self):
        uri = self.config.get("connection_string")
        client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = client[self.config["database"]]
        return True

    async def _connect_oracle(self):
        dsn = cx_Oracle.makedsn(
            self.config["host"],
            self.config["port"],
            service_name=self.config["database"],
        )
        self.connection = cx_Oracle.connect(
            self.config["user"],
            self.config["password"],
            dsn,
        )
        return True
