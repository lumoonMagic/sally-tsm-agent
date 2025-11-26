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
