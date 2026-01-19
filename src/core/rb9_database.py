"""
RB9 database connection handler for data synchronization.
Read/write operations using raw SQL queries with PascalCase columns.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import time

from src.core.config import config
from src.core.logger import logger


class Rb9DatabaseConnection:
    """
    Database connection handler for rb9_db (PascalCase schema).
    Provides read/write operations using raw SQL queries with connection pooling.
    """
    
    def __init__(self):
        # Build database URL for rb9_db
        self.database_url = f"postgresql://{config.RB9_DB_USER}:{config.RB9_DB_PASSWORD}@{config.RB9_DB_HOST}:{config.RB9_DB_PORT}/{config.RB9_DB_NAME}"
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection with connection pooling."""
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
            logger.info("RB9 database connection initialized with connection pooling")
        except Exception as e:
            logger.error(f"Failed to initialize RB9 database connection: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self):
        """Context manager for database session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"RB9 database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries.
        
        Args:
            query: SQL query string (use :param_name for parameters)
            params: Optional query parameters as dictionary
        
        Returns:
            List of dictionaries representing rows
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                with self.get_session() as session:
                    result = session.execute(text(query), params or {})
                    rows = result.fetchall()
                    
                    # Convert rows to dictionaries
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
    
    def check_record_exists(self, table_name: str, unique_field: str, unique_value: Any) -> bool:
        """
        Check if a record exists in the table by unique field.
        
        Args:
            table_name: Table name (PascalCase)
            unique_field: Unique field name (PascalCase)
            unique_value: Value to check
        
        Returns:
            True if record exists, False otherwise
        """
        query = f'SELECT "{unique_field}" FROM "{table_name}" WHERE "{unique_field}" = :unique_value LIMIT 1'
        result = self.execute_query(query, {'unique_value': unique_value})
        return len(result) > 0
    
    def get_record(self, table_name: str, unique_field: str, unique_value: Any) -> Optional[Dict[str, Any]]:
        """
        Get a single record by unique field.
        
        Args:
            table_name: Table name (PascalCase)
            unique_field: Unique field name (PascalCase)
            unique_value: Value to fetch
        
        Returns:
            Dictionary with record data or None if not found
        """
        query = f'SELECT * FROM "{table_name}" WHERE "{unique_field}" = :unique_value LIMIT 1'
        result = self.execute_query(query, {'unique_value': unique_value})
        return result[0] if result else None
    
    def execute_upsert(self, table_name: str, record: Dict[str, Any], unique_field: str, 
                      exclude_fields: Optional[List[str]] = None) -> bool:
        """
        Insert or update a record with CreateAtRb/UpdateAtRb tracking.
        
        Args:
            table_name: Table name (PascalCase)
            record: Dictionary with record data
            unique_field: Unique field name (PascalCase)
            exclude_fields: Fields to exclude from comparison (tracking fields, etc.)
        
        Returns:
            True if record was inserted/updated, False if skipped (no changes)
        """
        exclude_fields = exclude_fields or []
        exclude_fields.extend(['CreateAtRb', 'UpdateAtRb'])
        
        unique_value = record.get(unique_field)
        if not unique_value:
            logger.warning(f"Cannot upsert {table_name}: missing {unique_field}")
            return False
        
        # Check if record exists
        existing = self.get_record(table_name, unique_field, unique_value)
        
        if existing:
            # Update logic: compare fields and update if changed
            has_changes = False
            update_fields = []
            update_params = {'unique_value': unique_value}
            
            for field, value in record.items():
                if field in exclude_fields:
                    continue
                
                existing_value = existing.get(field)
                
                # Compare values (handle None cases)
                if existing_value != value:
                    # Check if both are None
                    if existing_value is None and value is None:
                        continue
                    # Check if one is None
                    if existing_value is None or value is None:
                        has_changes = True
                        update_fields.append(f'"{field}" = :{field}')
                        update_params[field] = value
                    else:
                        # Both have values, compare
                        if str(existing_value) != str(value):
                            has_changes = True
                            update_fields.append(f'"{field}" = :{field}')
                            update_params[field] = value
            
            if has_changes:
                # Update with UpdateAtRb
                update_fields.append('"UpdateAtRb" = NOW()')
                update_query = f'''
                    UPDATE "{table_name}"
                    SET {', '.join(update_fields)}
                    WHERE "{unique_field}" = :unique_value
                '''
                
                with self.get_session() as session:
                    session.execute(text(update_query), update_params)
                
                logger.debug(f"Updated {table_name} record with {unique_field}={unique_value}")
                return True
            else:
                logger.debug(f"No changes for {table_name} record with {unique_field}={unique_value}, skipping")
                return False
        else:
            # Insert new record with CreateAtRb
            fields = list(record.keys())
            field_names = [f'"{f}"' for f in fields]
            field_names.append('"CreateAtRb"')
            
            placeholders = [f':{field}' for field in fields]
            placeholders.append('NOW()')  # Use NOW() directly for CreateAtRb
            
            values = {field: record.get(field) for field in record.keys()}
            
            insert_query = f'''
                INSERT INTO "{table_name}" ({', '.join(field_names)})
                VALUES ({', '.join(placeholders)})
            '''
            
            with self.get_session() as session:
                session.execute(text(insert_query), values)
            
            logger.debug(f"Inserted {table_name} record with {unique_field}={unique_value}")
            return True
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("RB9 database connection test successful")
            return True
        except Exception as e:
            logger.error(f"RB9 database connection test failed: {str(e)}")
            return False
    
    def close(self):
        """Close all database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("RB9 database connection closed")

