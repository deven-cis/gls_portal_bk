
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import time

from src.core.config import config
from src.core.logger import logger


class Rb9DatabaseConnection:
    
    def __init__(self):
        self.database_url = f"postgresql://{config.RB9_DB_USER}:{config.RB9_DB_PASSWORD}@{config.RB9_DB_HOST}:{config.RB9_DB_PORT}/{config.RB9_DB_NAME}"
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
            logger.info("RB9 database connection initialized with connection pooling")
        except Exception as e:
            logger.error(f"Failed to initialize RB9 database connection: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self):
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
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                with self.get_session() as session:
                    result = session.execute(text(query), params or {})
                    rows = result.fetchall()
                    
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

        query = f'SELECT "{unique_field}" FROM "{table_name}" WHERE "{unique_field}" = :unique_value LIMIT 1'
        result = self.execute_query(query, {'unique_value': unique_value})
        return len(result) > 0
    
    def get_record(self, table_name: str, unique_field: str, unique_value: Any) -> Optional[Dict[str, Any]]:
        
        query = f'SELECT * FROM "{table_name}" WHERE "{unique_field}" = :unique_value LIMIT 1'
        result = self.execute_query(query, {'unique_value': unique_value})
        return result[0] if result else None
    
    def execute_upsert(self, table_name: str, record: Dict[str, Any], unique_field: str, 
                      exclude_fields: Optional[List[str]] = None) -> bool:
        
        exclude_fields = exclude_fields or []
        exclude_fields.extend(['CreateAtRb', 'UpdateAtRb'])
        
        unique_value = record.get(unique_field)
        if not unique_value:
            logger.warning(f"Cannot upsert {table_name}: missing {unique_field}")
            return False
        
        existing = self.get_record(table_name, unique_field, unique_value)
        
        if existing:
            has_changes = False
            update_fields = []
            update_params = {'unique_value': unique_value}
            
            for field, value in record.items():
                if field in exclude_fields:
                    continue
                
                existing_value = existing.get(field)
                
                if existing_value != value:
                    if existing_value is None and value is None:
                        continue
                    if existing_value is None or value is None:
                        has_changes = True
                        update_fields.append(f'"{field}" = :{field}')
                        update_params[field] = value
                    else:
                        if str(existing_value) != str(value):
                            has_changes = True
                            update_fields.append(f'"{field}" = :{field}')
                            update_params[field] = value
            
            if has_changes:
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
            fields = list(record.keys())
            field_names = [f'"{f}"' for f in fields]
            field_names.append('"CreateAtRb"')
            
            placeholders = [f':{field}' for field in fields]
            placeholders.append('NOW()')
            
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
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("RB9 database connection test successful")
            return True
        except Exception as e:
            logger.error(f"RB9 database connection test failed: {str(e)}")
            return False
    
    def close(self):
        if self.engine:
            self.engine.dispose()
            logger.info("RB9 database connection closed")

