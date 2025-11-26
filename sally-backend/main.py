"""
Sally TSM Backend - Main API Server
FastAPI backend for Sally Trial Supply Management Agent
Supports: PostgreSQL, MySQL, Oracle, SQLite + Gemini AI
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
import os
import json
from dotenv import load_dotenv
import logging

from database.manager import DatabaseManager
from ai.gemini_agent import GeminiAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sally TSM Backend",
    description="AI-powered Trial Supply Management Backend with Gemini integration",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_manager = DatabaseManager()
gemini_api_key = os.getenv("GEMINI_API_KEY", "")
ai_agent = GeminiAgent(api_key=gemini_api_key) if gemini_api_key else None

# ============================================================================
# Pydantic Models
# ============================================================================

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    include_visualization: bool = Field(default=True, description="Include chart suggestions")

class ExecuteRequest(BaseModel):
    sql_query: str = Field(..., description="SQL query to execute")
    include_visualization: bool = Field(default=True, description="Include visualization")

class DatabaseConfigRequest(BaseModel):
    type: Literal['postgresql', 'mysql', 'oracle', 'sqlite'] = Field(..., description="Database type")
    host: Optional[str] = Field(None, description="Database host")
    port: Optional[int] = Field(None, description="Database port")
    database: str = Field(..., description="Database name")
    username: Optional[str] = Field(None, description="Database username")
    password: Optional[str] = Field(None, description="Database password")

class LLMConfigRequest(BaseModel):
    provider: Literal['gemini', 'openai', 'claude'] = Field(..., description="LLM provider")
    api_key: str = Field(..., description="API key for the LLM")
    model: Optional[str] = Field("gemini-pro", description="Model name")

class QueryResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    explanation: Optional[str] = None
    requires_approval: bool = True

class ExecuteResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    visualization: Optional[Dict[str, Any]] = None
    row_count: int = 0
    error: Optional[str] = None

class ConfigResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "name": "Sally TSM Backend",
        "version": "1.0.0",
        "status": "running",
        "gemini_configured": ai_agent is not None,
        "database_connected": db_manager.is_connected()
    }

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": {
            "connected": db_manager.is_connected(),
            "type": db_manager.db_type if db_manager.is_connected() else None
        },
        "ai": {
            "configured": ai_agent is not None,
            "provider": "gemini" if ai_agent else None
        }
    }

@app.post("/api/v1/query/ask", response_model=QueryResponse, tags=["Query"])
async def process_query(request: QueryRequest):
    """
    Process natural language query with Gemini AI
    
    Converts user's natural language question into SQL query
    Returns SQL and explanation for user approval
    """
    try:
        if not ai_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini AI not configured. Please configure API key first."
            )
        
        if not db_manager.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not connected. Please configure database first."
            )
        
        # Get database schema
        schema = await db_manager.get_schema()
        
        # Generate SQL with Gemini
        logger.info(f"Processing query: {request.query}")
        result = await ai_agent.generate_sql(request.query, schema)
        
        logger.info(f"Generated SQL: {result['sql']}")
        
        return QueryResponse(
            success=True,
            sql=result["sql"],
            explanation=result["explanation"],
            requires_approval=True
        )
    
    except Exception as e:
        logger.error(f"Query processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )

@app.post("/api/v1/query/execute", response_model=ExecuteResponse, tags=["Query"])
async def execute_query(request: ExecuteRequest):
    """
    Execute approved SQL query
    
    Runs the user-approved SQL query on the database
    Returns data and optional visualization suggestions
    """
    try:
        if not db_manager.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not connected"
            )
        
        # Validate query safety
        if not ai_agent or not ai_agent.is_safe_query(request.sql_query):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsafe query detected. Only SELECT queries are allowed."
            )
        
        # Execute query
        logger.info(f"Executing SQL: {request.sql_query}")
        data = await db_manager.execute_query(request.sql_query)
        
        # Generate visualization suggestion if requested
        visualization = None
        if request.include_visualization and data:
            visualization = await ai_agent.suggest_visualization(data)
        
        logger.info(f"Query returned {len(data)} rows")
        
        return ExecuteResponse(
            success=True,
            data=data,
            visualization=visualization,
            row_count=len(data) if data else 0
        )
    
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        return ExecuteResponse(
            success=False,
            error=str(e),
            row_count=0
        )

@app.post("/api/v1/config/database", response_model=ConfigResponse, tags=["Configuration"])
async def configure_database(config: DatabaseConfigRequest):
    """
    Configure database connection
    
    Tests and establishes connection to the specified database
    Supports: PostgreSQL, MySQL, Oracle, SQLite
    """
    try:
        logger.info(f"Configuring database: {config.type}")
        
        # Test connection
        success = await db_manager.connect(config.dict())
        
        if success:
            logger.info("Database connection successful")
            return ConfigResponse(
                success=True,
                message=f"Successfully connected to {config.type} database"
            )
        else:
            logger.warning("Database connection failed")
            return ConfigResponse(
                success=False,
                message="Connection failed",
                error="Could not connect to database. Please check credentials."
            )
    
    except Exception as e:
        logger.error(f"Database configuration error: {str(e)}")
        return ConfigResponse(
            success=False,
            message="Configuration failed",
            error=str(e)
        )

@app.post("/api/v1/config/llm", response_model=ConfigResponse, tags=["Configuration"])
async def configure_llm(config: LLMConfigRequest):
    """
    Configure LLM provider
    
    Sets up Gemini AI with the provided API key
    Tests connection to ensure key is valid
    """
    global ai_agent
    
    try:
        logger.info(f"Configuring LLM: {config.provider}")
        
        # Create new agent with provided key
        ai_agent = GeminiAgent(api_key=config.api_key)
        
        # Test connection
        success = await ai_agent.test_connection()
        
        if success:
            logger.info("LLM configuration successful")
            return ConfigResponse(
                success=True,
                message=f"Successfully configured {config.provider}"
            )
        else:
            logger.warning("LLM connection test failed")
            ai_agent = None
            return ConfigResponse(
                success=False,
                message="Configuration failed",
                error="Invalid API key or connection failed"
            )
    
    except Exception as e:
        logger.error(f"LLM configuration error: {str(e)}")
        ai_agent = None
        return ConfigResponse(
            success=False,
            message="Configuration failed",
            error=str(e)
        )

@app.get("/api/v1/config/status", tags=["Configuration"])
async def get_config_status():
    """Get current configuration status"""
    return {
        "database": {
            "connected": db_manager.is_connected(),
            "type": db_manager.db_type if db_manager.is_connected() else None,
            "status": "connected" if db_manager.is_connected() else "not_configured"
        },
        "llm": {
            "configured": ai_agent is not None,
            "provider": "gemini" if ai_agent else None,
            "status": "ready" if ai_agent else "not_configured"
        }
    }

# ============================================================================
# Data Endpoints (Convenience methods for common queries)
# ============================================================================

@app.get("/api/v1/data/sites", tags=["Data"])
async def get_sites():
    """Get all sites"""
    try:
        if not db_manager.is_connected():
            return []
        
        data = await db_manager.execute_query("SELECT * FROM sites ORDER BY name")
        return data or []
    except Exception as e:
        logger.error(f"Error fetching sites: {str(e)}")
        return []

@app.get("/api/v1/data/inventory", tags=["Data"])
async def get_inventory():
    """Get all inventory"""
    try:
        if not db_manager.is_connected():
            return []
        
        data = await db_manager.execute_query("SELECT * FROM inventory ORDER BY last_updated DESC")
        return data or []
    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        return []

@app.get("/api/v1/data/shipments", tags=["Data"])
async def get_shipments():
    """Get all shipments"""
    try:
        if not db_manager.is_connected():
            return []
        
        data = await db_manager.execute_query("SELECT * FROM shipments ORDER BY shipped_date DESC")
        return data or []
    except Exception as e:
        logger.error(f"Error fetching shipments: {str(e)}")
        return []

@app.get("/api/v1/data/studies", tags=["Data"])
async def get_studies():
    """Get all studies"""
    try:
        if not db_manager.is_connected():
            return []
        
        data = await db_manager.execute_query("SELECT * FROM studies ORDER BY name")
        return data or []
    except Exception as e:
        logger.error(f"Error fetching studies: {str(e)}")
        return []

@app.get("/api/v1/data/vendors", tags=["Data"])
async def get_vendors():
    """Get all vendors"""
    try:
        if not db_manager.is_connected():
            return []
        
        data = await db_manager.execute_query("SELECT * FROM vendors ORDER BY name")
        return data or []
    except Exception as e:
        logger.error(f"Error fetching vendors: {str(e)}")
        return []

@app.get("/api/v1/data/tasks", tags=["Data"])
async def get_tasks():
    """Get all tasks"""
    try:
        if not db_manager.is_connected():
            return []
        
        data = await db_manager.execute_query("SELECT * FROM tasks ORDER BY due_date")
        return data or []
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        return []

# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("="*60)
    logger.info("Sally TSM Backend Starting...")
    logger.info("="*60)
    
    if gemini_api_key:
        logger.info("✓ Gemini API key found")
    else:
        logger.warning("⚠ Gemini API key not configured")
    
    logger.info("="*60)
@app.get("/api/v1/database/test")
async def test_database():
    """Test database connection"""
    import os
    import psycopg2
    
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        return {
            "success": False,
            "message": "DATABASE_URL not configured"
        }
    
    try:
        # Try to connect
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Database connection successful",
            "database_version": version[:50]  # First 50 chars
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
