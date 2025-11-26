"""
Gemini AI Agent for Sally TSM
Handles natural language to SQL conversion using Google Gemini API
"""

import google.generativeai as genai
import json
import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GeminiAgent:
    """Gemini AI Agent for SQL generation and query processing"""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini Agent
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.model = None
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.model = None
        else:
            logger.warning("Gemini API key not provided")
    
    async def test_connection(self) -> bool:
        """
        Test Gemini API connection
        
        Returns:
            bool: True if connection successful
        """
        if not self.model:
            return False
        
        try:
            response = await self.model.generate_content_async("Hello, test connection")
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
    
    async def generate_sql(self, query: str, schema: Dict) -> Dict[str, str]:
        """
        Generate SQL from natural language query
        
        Args:
            query: Natural language question
            schema: Database schema information
            
        Returns:
            dict: Contains 'sql' and 'explanation' keys
        """
        if not self.model:
            raise Exception("Gemini API not configured")
        
        # Build comprehensive prompt
        prompt = self._build_sql_generation_prompt(query, schema)
        
        try:
            logger.info(f"Generating SQL for query: {query}")
            response = await self.model.generate_content_async(prompt)
            text = response.text
            
            # Parse response
            sql, explanation = self._parse_gemini_response(text)
            
            logger.info(f"Generated SQL: {sql}")
            
            return {
                "sql": sql,
                "explanation": explanation
            }
        
        except Exception as e:
            logger.error(f"SQL generation failed: {str(e)}")
            raise Exception(f"Failed to generate SQL: {str(e)}")
    
    def _build_sql_generation_prompt(self, query: str, schema: Dict) -> str:
        """Build comprehensive prompt for SQL generation"""
        
        schema_text = self._format_schema(schema)
        
        prompt = f"""You are an expert SQL assistant for a Trial Supply Management (TSM) system.

DATABASE SCHEMA:
{schema_text}

USER QUESTION: {query}

INSTRUCTIONS:
1. Generate a safe SELECT SQL query to answer the user's question
2. Use only tables and columns from the schema provided
3. Include appropriate JOINs if multiple tables are needed
4. Add WHERE clauses to filter relevant data
5. Use aggregate functions (COUNT, SUM, AVG) when appropriate
6. Add ORDER BY for better readability
7. Limit results to prevent overwhelming data (LIMIT 100)

SAFETY RULES:
- ONLY generate SELECT queries
- NO INSERT, UPDATE, DELETE, DROP, or any data modification
- NO subqueries that could cause performance issues
- NO UNION or complex nested queries unless necessary

OUTPUT FORMAT:
Provide your response in exactly this format:

SQL:
<your complete SQL query here>

EXPLANATION:
<brief explanation of what the query does and what it returns>

Now generate the SQL query:"""
        
        return prompt
    
    def _format_schema(self, schema: Dict) -> str:
        """Format schema for prompt"""
        if not schema or 'tables' not in schema:
            return "No schema available"
        
        formatted = []
        for table in schema.get('tables', []):
            table_name = table.get('name', 'unknown')
            columns = table.get('columns', [])
            
            formatted.append(f"\nTable: {table_name}")
            formatted.append("Columns:")
            
            for col in columns:
                col_name = col.get('name', 'unknown')
                col_type = col.get('type', 'unknown')
                formatted.append(f"  - {col_name} ({col_type})")
        
        return "\n".join(formatted)
    
    def _parse_gemini_response(self, text: str) -> tuple:
        """
        Parse Gemini's response to extract SQL and explanation
        
        Args:
            text: Raw response from Gemini
            
        Returns:
            tuple: (sql_query, explanation)
        """
        # Try to extract SQL
        sql_match = re.search(r'SQL:\s*(.+?)(?=EXPLANATION:|$)', text, re.DOTALL | re.IGNORECASE)
        exp_match = re.search(r'EXPLANATION:\s*(.+)', text, re.DOTALL | re.IGNORECASE)
        
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Fallback: try to find SQL in code blocks
            code_block = re.search(r'```sql\s*(.+?)\s*```', text, re.DOTALL | re.IGNORECASE)
            if code_block:
                sql = code_block.group(1).strip()
            else:
                sql = text.strip()
        
        explanation = exp_match.group(1).strip() if exp_match else "Query generated by Gemini AI"
        
        # Clean SQL
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        # Remove any text before SELECT
        if 'select' in sql.lower():
            sql = sql[sql.lower().index('select'):]
        
        return sql, explanation
    
    def is_safe_query(self, sql: str) -> bool:
        """
        Validate that SQL query is safe to execute
        
        Args:
            sql: SQL query to validate
            
        Returns:
            bool: True if query is safe
        """
        if not sql:
            return False
        
        sql_lower = sql.lower().strip()
        
        # Must start with SELECT
        if not sql_lower.startswith('select'):
            logger.warning(f"Query rejected: Must start with SELECT")
            return False
        
        # Block dangerous keywords
        dangerous_keywords = [
            'drop', 'delete', 'truncate', 'alter', 'create',
            'insert', 'update', 'grant', 'revoke', 'exec',
            'execute', 'xp_', 'sp_', 'shutdown', 'backup',
            'restore', 'use ', 'into outfile', 'into dumpfile',
            'load_file', 'system', 'shell'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                logger.warning(f"Query rejected: Contains dangerous keyword '{keyword}'")
                return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r';\s*drop',  # Multiple statements
            r'--\s*drop',  # SQL injection attempt
            r'/\*.*\*/',  # Block comments (could hide malicious code)
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, sql_lower):
                logger.warning(f"Query rejected: Matches suspicious pattern")
                return False
        
        logger.info("Query validated: SAFE")
        return True
    
    async def suggest_visualization(self, data: List[Dict]) -> Optional[Dict]:
        """
        Suggest appropriate visualization for query results
        
        Args:
            data: Query result data
            
        Returns:
            dict: Visualization suggestion or None
        """
        if not data or len(data) == 0:
            return None
        
        try:
            # Get column names and sample data
            columns = list(data[0].keys())
            
            # Simple heuristics for visualization
            # In production, could use Gemini to suggest best chart type
            
            if len(columns) < 2:
                return None
            
            # Check for numerical data
            numerical_cols = []
            categorical_cols = []
            
            for col in columns:
                sample_value = data[0][col]
                if isinstance(sample_value, (int, float)):
                    numerical_cols.append(col)
                else:
                    categorical_cols.append(col)
            
            # Suggest visualization based on data structure
            if len(categorical_cols) >= 1 and len(numerical_cols) >= 1:
                # Category vs Number -> Bar chart
                return {
                    "type": "bar",
                    "x_axis": categorical_cols[0],
                    "y_axis": numerical_cols[0],
                    "title": f"{numerical_cols[0]} by {categorical_cols[0]}",
                    "description": "Bar chart showing distribution"
                }
            
            elif len(numerical_cols) >= 2:
                # Two numbers -> Line chart or scatter
                return {
                    "type": "line",
                    "x_axis": numerical_cols[0],
                    "y_axis": numerical_cols[1],
                    "title": f"{numerical_cols[1]} vs {numerical_cols[0]}",
                    "description": "Trend visualization"
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Visualization suggestion failed: {e}")
            return None
    
    async def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to understand intent
        
        Args:
            query: Natural language query
            
        Returns:
            dict: Intent analysis
        """
        query_lower = query.lower()
        
        intent = {
            "type": "general",
            "entities": [],
            "metrics": [],
            "filters": []
        }
        
        # Detect query type
        if any(word in query_lower for word in ['show', 'list', 'display', 'get']):
            intent["type"] = "retrieve"
        elif any(word in query_lower for word in ['count', 'how many', 'number of']):
            intent["type"] = "aggregate"
        elif any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            intent["type"] = "compare"
        elif any(word in query_lower for word in ['trend', 'over time', 'timeline']):
            intent["type"] = "trend"
        
        # Detect entities
        entities_map = {
            'sites': ['site', 'location', 'facility'],
            'inventory': ['inventory', 'stock', 'supplies'],
            'shipments': ['shipment', 'delivery', 'shipping'],
            'vendors': ['vendor', 'supplier'],
            'studies': ['study', 'trial'],
            'tasks': ['task', 'action', 'priority']
        }
        
        for entity, keywords in entities_map.items():
            if any(kw in query_lower for kw in keywords):
                intent["entities"].append(entity)
        
        return intent


# Utility function for initialization
def create_gemini_agent(api_key: Optional[str] = None) -> Optional[GeminiAgent]:
    """
    Factory function to create Gemini agent
    
    Args:
        api_key: Optional API key (will use env var if not provided)
        
    Returns:
        GeminiAgent instance or None if not configured
    """
    import os
    
    key = api_key or os.getenv("GEMINI_API_KEY")
    
    if not key:
        logger.warning("No Gemini API key provided")
        return None
    
    return GeminiAgent(api_key=key)
