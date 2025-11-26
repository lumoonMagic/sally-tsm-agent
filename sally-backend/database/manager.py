"""
Database Manager for Sally TSM
Supports: PostgreSQL, MySQL, Oracle, SQLite
"""

import asyncpg  # PostgreSQL
import aiomysql  # MySQL
import aiosqlite  # SQLite
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Multi-database connection manager"""
    
    def __init__(self):
        """Initialize database manager"""
        self.connection = None
        self.db_type = None
        self.config = None
    
    async def connect(self, config: Dict) -> bool:
        """
        Connect to database based on configuration
        
        Args:
            config: Database configuration dictionary
                - type: postgresql, mysql, oracle, sqlite
                - host, port, database, username, password
                
        Returns:
            bool: True if connection successful
        """
        self.config = config
        self.db_type = config['type']
        
        try:
            logger.info(f"Connecting to {self.db_type} database...")
            
            if self.db_type == 'postgresql':
                await self._connect_postgresql(config)
            elif self.db_type == 'mysql':
                await self._connect_mysql(config)
            elif self.db_type == 'sqlite':
                await self._connect_sqlite(config)
            elif self.db_type == 'oracle':
                await self._connect_oracle(config)
            else:
                raise Exception(f"Unsupported database type: {self.db_type}")
            
            logger.info(f"Successfully connected to {self.db_type}")
            return True
        
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            self.connection = None
            return False
    
    async def _connect_postgresql(self, config: Dict):
        """Connect to PostgreSQL"""
        self.connection = await asyncpg.create_pool(
            host=config['host'],
            port=config['port'] or 5432,
            database=config['database'],
            user=config['username'],
            password=config['password'],
            min_size=1,
            max_size=10
        )
    
    async def _connect_mysql(self, config: Dict):
        """Connect to MySQL"""
        self.connection = await aiomysql.create_pool(
            host=config['host'],
            port=config['port'] or 3306,
            db=config['database'],
            user=config['username'],
            password=config['password'],
            minsize=1,
            maxsize=10
        )
    
    async def _connect_sqlite(self, config: Dict):
        """Connect to SQLite"""
        self.connection = await aiosqlite.connect(config['database'])
    
    async def _connect_oracle(self, config: Dict):
        """Connect to Oracle (placeholder)"""
        # Oracle async support requires cx_Oracle with proper async configuration
        # This is a simplified placeholder
        raise NotImplementedError("Oracle support requires additional configuration")
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.connection is not None
    
    async def execute_query(self, sql: str) -> List[Dict]:
        """
        Execute SELECT query
        
        Args:
            sql: SQL SELECT query
            
        Returns:
            List of dictionaries with query results
        """
        if not self.is_connected():
            raise Exception("Database not connected")
        
        try:
            logger.info(f"Executing query on {self.db_type}")
            
            if self.db_type == 'postgresql':
                return await self._execute_postgresql(sql)
            elif self.db_type == 'mysql':
                return await self._execute_mysql(sql)
            elif self.db_type == 'sqlite':
                return await self._execute_sqlite(sql)
            else:
                raise Exception(f"Execute not implemented for {self.db_type}")
        
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise Exception(f"Query execution failed: {str(e)}")
    
    async def _execute_postgresql(self, sql: str) -> List[Dict]:
        """Execute query on PostgreSQL"""
        async with self.connection.acquire() as conn:
            rows = await conn.fetch(sql)
            return [dict(row) for row in rows]
    
    async def _execute_mysql(self, sql: str) -> List[Dict]:
        """Execute query on MySQL"""
        async with self.connection.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql)
                rows = await cursor.fetchall()
                return rows
    
    async def _execute_sqlite(self, sql: str) -> List[Dict]:
        """Execute query on SQLite"""
        async with self.connection.execute(sql) as cursor:
            rows = await cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    async def get_schema(self) -> Dict:
        """
        Get database schema information
        
        Returns:
            Dictionary with schema information
        """
        if not self.is_connected():
            return {"tables": []}
        
        try:
            logger.info(f"Retrieving schema from {self.db_type}")
            
            if self.db_type == 'postgresql':
                return await self._get_schema_postgresql()
            elif self.db_type == 'mysql':
                return await self._get_schema_mysql()
            elif self.db_type == 'sqlite':
                return await self._get_schema_sqlite()
            else:
                return {"tables": []}
        
        except Exception as e:
            logger.error(f"Schema retrieval failed: {str(e)}")
            return {"tables": []}
    
    async def _get_schema_postgresql(self) -> Dict:
        """Get PostgreSQL schema"""
        sql = """
            SELECT 
                table_name, 
                column_name, 
                data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """
        
        rows = await self._execute_postgresql(sql)
        return self._build_schema_from_rows(rows)
    
    async def _get_schema_mysql(self) -> Dict:
        """Get MySQL schema"""
        sql = """
            SELECT 
                table_name, 
                column_name, 
                data_type 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE()
            ORDER BY table_name, ordinal_position
        """
        
        rows = await self._execute_mysql(sql)
        return self._build_schema_from_rows(rows)
    
    async def _get_schema_sqlite(self) -> Dict:
        """Get SQLite schema"""
        # Get table names
        tables_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        async with self.connection.execute(tables_sql) as cursor:
            table_rows = await cursor.fetchall()
        
        tables = []
        
        for (table_name,) in table_rows:
            # Get columns for each table
            columns_sql = f"PRAGMA table_info({table_name})"
            async with self.connection.execute(columns_sql) as cursor:
                column_rows = await cursor.fetchall()
            
            columns = []
            for col_row in column_rows:
                columns.append({
                    "name": col_row[1],
                    "type": col_row[2]
                })
            
            tables.append({
                "name": table_name,
                "columns": columns
            })
        
        return {"tables": tables}
    
    def _build_schema_from_rows(self, rows: List[Dict]) -> Dict:
        """Build schema structure from query rows"""
        tables_dict = {}
        
        for row in rows:
            table_name = row.get('table_name')
            column_name = row.get('column_name')
            data_type = row.get('data_type')
            
            if table_name not in tables_dict:
                tables_dict[table_name] = {
                    "name": table_name,
                    "columns": []
                }
            
            tables_dict[table_name]["columns"].append({
                "name": column_name,
                "type": data_type
            })
        
        return {"tables": list(tables_dict.values())}
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            try:
                if self.db_type == 'postgresql':
                    await self.connection.close()
                elif self.db_type == 'mysql':
                    self.connection.close()
                    await self.connection.wait_closed()
                elif self.db_type == 'sqlite':
                    await self.connection.close()
                
                logger.info(f"Closed {self.db_type} connection")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
            
            self.connection = None
            self.db_type = None
