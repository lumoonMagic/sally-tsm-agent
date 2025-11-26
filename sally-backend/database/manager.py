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

# SQLite (optional)
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

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.connection = None
        self.db = None

    # -----------------------------------------------------
    # Connection Logic
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Helper Methods (Restored)
    # -----------------------------------------------------

    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.connection is not None or self.db is not None

    async def disconnect(self):
        """Close database connection safely"""

        if isinstance(self.connection, asyncpg.pool.Pool):
            await self.connection.close()

        elif isinstance(self.connection, aiomysql.Pool):
            self.connection.close()
            await self.connection.wait_closed()

        elif SQLITE_AVAILABLE and isinstance(self.connection, aiosqlite.Connection):
            await self.connection.close()

        elif ORACLE_AVAILABLE and isinstance(self.connection, cx_Oracle.Connection):
            self.connection.close()

        elif MONGODB_AVAILABLE and self.db:
            self.db.client.close()

        self.connection = None
        self.db = None

    # -----------------------------------------------------
    # Query Execution
    # -----------------------------------------------------

    async def execute_query(self, query: str) -> List[Dict]:
        """Route query to the appropriate database engine"""

        db_type = self.config.get("type", "").lower()

        if db_type in ("postgres", "postgresql"):
            return await self._execute_postgres(query)

        elif db_type == "mysql":
            return await self._execute_mysql(query)

        elif db_type == "sqlite":
            return await self._execute_sqlite(query)

        elif db_type == "mongodb":
            return await self._execute_mongodb(query)

        elif db_type == "oracle":
            return await self._execute_oracle(query)

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    # ----------- SQL Executors -----------

    async def _execute_postgres(self, query: str):
        async with self.connection.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]

    async def _execute_mysql(self, query: str):
        async with self.connection.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query)
                return await cur.fetchall()

    async def _execute_sqlite(self, query: str):
        async with self.connection.execute(query) as cursor:
            rows = await cursor.fetchall()
            columns = [c[0] for c in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def _execute_oracle(self, query: str):
        cursor = self.connection.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    async def _execute_mongodb(self, query: str) -> List[Dict]:
        """
        Very basic MongoDB query executor:
        query = { "collection": "inventory", "filter": {}, "limit": 10 }
        """
        if not isinstance(query, dict):
            raise ValueError("MongoDB queries must be JSON dictionaries")

        collection = query.get("collection")
        filter_q = query.get("filter", {})
        limit = query.get("limit", 100)

        cursor = self.db[collection].find(filter_q).limit(limit)
        return [doc async for doc in cursor]

    # -----------------------------------------------------
    # Schema + Seed (Simple versions)
    # -----------------------------------------------------

    async def create_schema(self, schema: Dict[str, str]) -> bool:
        """
        schema example:
        {
            "inventory": "CREATE TABLE inventory(id SERIAL PRIMARY KEY, ...)"
        }
        """
        for table, ddl in schema.items():
            await self.execute_query(ddl)

        return True

    async def seed_data(self, table: str, data: List[Dict]) -> int:
        if not data:
            return 0

        db_type = self.config.get("type", "")

        if db_type == "mongodb":
            result = await self.db[table].insert_many(data)
            return len(result.inserted_ids)

        # SQL insert
        keys = data[0].keys()
        columns = ", ".join(keys)

        values_list = []
        for row in data:
            row_values = ", ".join([f"'{str(v)}'" for v in row.values()])
            values_list.append(f"({row_values})")

        sql = f"INSERT INTO {table} ({columns}) VALUES " + ", ".join(values_list)

        await self.execute_query(sql)
        return len(data)
