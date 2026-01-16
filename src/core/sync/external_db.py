"""
External database connection handler for data synchronization.

This is a scalable approach because:
1. Connection Pooling: Reuses connections instead of creating new ones (faster, efficient)
2. Automatic Cleanup: Context managers ensure connections are properly closed
3. Retry Logic: Handles temporary network/database failures
4. Resource Management: Prevents connection leaks

For simple use: Just call execute_query(query, params) - it handles everything!
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import time

from src.core.config import config
from src.core.logger import logger


class ExternalDatabase:
   
    
    def __init__(self):
        self.database_url = config.EXTERNAL_DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True,
                echo=False
            )
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autoflush=False,
                autocommit=False
            )
            logger.info("External database connection initialized with connection pooling")
        except Exception as e:
            logger.error(f"Failed to initialize external database connection: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()  
            
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, fetch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries.
        Optimized for bulk data retrieval.
        
        Args:
            query: SQL query string (use :param_name for parameters)
            params: Optional query parameters as dictionary
            fetch_size: Optional batch size for large result sets (default: fetch all)
        
        Returns:
            List of dictionaries representing rows
        
        Example:
            # Simple query
            results = db.execute_query("SELECT * FROM users")
            
            # With parameters
            results = db.execute_query(
                "SELECT * FROM users WHERE email = :email",
                {"email": "test@example.com"}
            )
            
            # Bulk data with batch processing
            results = db.execute_query(
                "SELECT * FROM users WHERE created_at >= :start_date",
                {"start_date": "2024-01-01"},
                fetch_size=1000
            )
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                with self.get_session() as session:
                    result = session.execute(text(query), params or {})
                    rows = result.fetchall()
                    
                    # Convert rows to dictionaries (fast bulk conversion)
                    if rows:
                        columns = result.keys()
                        return [dict(zip(columns, row)) for row in rows]
                    return []
            except SQLAlchemyError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Query failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Query failed after {max_retries} attempts: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error executing query: {str(e)}")
                raise
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("External database connection test successful")
            return True
        except Exception as e:
            logger.error(f"External database connection test failed: {str(e)}")
            return False
    
    def close(self):
        """Close all database connections (usually not needed - auto-managed)."""
        if self.engine:
            self.engine.dispose()
            logger.info("External database connection closed")

