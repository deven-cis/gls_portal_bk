"""
Main sync service with upsert logic for data synchronization.
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.core.database import SessionLocal
from src.core.logger import logger
from src.core.sync.external_db import ExternalDatabase


class SyncService:
    
    def __init__(self, external_db: Optional[ExternalDatabase] = None):
        self.external_db = external_db or ExternalDatabase()
        logger.info("Using external database for sync")
        
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def sync_table(
        self,
        table_name: str,
        unique_field: str,
        external_query: str = None,
        local_model: Any = None,
        field_mapping: Optional[Dict[str, str]] = None,
        date_field: str = 'LastModified',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transform_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        fetch_size: Optional[int] = 2
    ) -> Dict[str, int]:
        """
        Sync a table from external database to local database.
        
        Args:
            table_name: Name of the table being synced (for logging)
            unique_field: Field name used as unique identifier (e.g., 'case_no', 'job_no', 'user_no')
            external_query: SQL query to fetch data from external database
            local_model: SQLAlchemy model class for local table
            field_mapping: Optional mapping of external field names to local field names
            date_field: Field name to use for date filtering (default: 'last_modified_at')
            start_date: Start date for filtering (if None, uses all records)
            end_date: End date for filtering (if None, uses current time)
            transform_func: Optional function to transform external data before syncing
        
        Returns:
            Dictionary with sync statistics
        """
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        try:
            logger.info(f"Starting sync for {table_name} from external database")
            
            # Build query with date filter if provided
            query = external_query.strip()
            params = {}
            where_clauses = []
            
            # Add LastModified >= start_date filter
            if start_date and date_field:
                where_clauses.append(f"{date_field} >= :start_date")
                params['start_date'] = start_date
                logger.info(f"Filtering by {date_field} >= {start_date}")
            
            # Add LastModified <= end_date filter
            if end_date and date_field:
                where_clauses.append(f"{date_field} <= :end_date")
                params['end_date'] = end_date
                logger.info(f"Filtering by {date_field} <= {end_date}")
            
            # Add WHERE clause if we have date filters
            if where_clauses:
                where_clause = " AND ".join(where_clauses)
                if 'WHERE' in query.upper():
                    query += f" AND {where_clause}"
                else:
                    query += f" WHERE {where_clause}"
            
            # Log the final query (without parameters for security)
            logger.info(f"Executing query for {table_name}: {query}...")
            logger.info(f"Params: {params}")
            logger.info(f"Fetch size: {fetch_size}")
            # logger.info(f"query-------------------", query)
            
            # Fetch data from external database (optimized for bulk data)
            # external_records=[]
            external_records = self.external_db.execute_query(query, params, fetch_size=fetch_size)
            logger.info(f"Fetched {len(external_records)} records from external {table_name} table (filtered by {date_field})")
            
            if not external_records:
                logger.info(f"No records to sync for {table_name}")
                return self.stats
            
            # Process records in batches
            local_session = SessionLocal()
            try:
                for record in external_records:
                    try:
                        # Transform record if transform function provided
                        if transform_func:
                            record = transform_func(record)
                        
                    
                        if field_mapping:
                            mapped_record = {}
                            # Map fields according to mapping
                            for ext_field, local_field in field_mapping.items():
                                if ext_field in record:
                                    mapped_record[local_field] = record[ext_field]
                            # Add unmapped fields (fields that exist in record but not in mapping)
                            for key, value in record.items():
                                if key not in field_mapping:
                                    # Keep original field name if not in mapping
                                    mapped_record[key] = value
                            record = mapped_record
                        
                        # Get unique identifier value
                        unique_value = record.get(unique_field)
                        if not unique_value:
                            logger.warning(f"Skipping record in {table_name} - missing {unique_field}")
                            self.stats['skipped'] += 1
                            continue
                        
                        # Check if record exists locally
                        existing_record = local_session.query(local_model).filter(
                            getattr(local_model, unique_field) == unique_value
                        ).first()
                        
                        if existing_record:
                            # Update existing record
                            updated = self._update_record(existing_record, record, table_name)
                            if updated:
                                self.stats['updated'] += 1
                            else:
                                self.stats['skipped'] += 1
                        else:
                            # Insert new record
                            new_record = self._create_record(local_model, record, table_name)
                            if new_record:
                                local_session.add(new_record)
                                self.stats['inserted'] += 1
                            else:
                                self.stats['skipped'] += 1
                        
                        # Commit in batches to avoid long transactions
                        if (self.stats['inserted'] + self.stats['updated']) % 50 == 0:
                            local_session.commit()
                            logger.debug(f"Committed batch for {table_name}")
                    
                    except Exception as e:
                        logger.error(f"Error processing record in {table_name}: {str(e)}")
                        self.stats['errors'] += 1
                        continue
                
                # Final commit
                local_session.commit()
                logger.info(
                    f"Completed sync for {table_name}: "
                    f"Inserted={self.stats['inserted']}, "
                    f"Updated={self.stats['updated']}, "
                    f"Errors={self.stats['errors']}, "
                    f"Skipped={self.stats['skipped']}"
                )
            
            except SQLAlchemyError as e:
                local_session.rollback()
                logger.error(f"Database error during {table_name} sync: {str(e)}")
                self.stats['errors'] += len(external_records)
                raise
            finally:
                local_session.close()
        
        except Exception as e:
            logger.error(f"Failed to sync {table_name}: {str(e)}", exc_info=True)
            self.stats['errors'] += 1
            raise
        
        return self.stats
    
    def _update_record(
        self,
        existing_record: Any,
        new_data: Dict[str, Any],
        table_name: str
    ) -> bool:
        """
        Update an existing record with new data if changes detected.
        
        Args:
            existing_record: Existing SQLAlchemy model instance
            new_data: Dictionary with new data
            table_name: Table name for logging
        
        Returns:
            True if record was updated, False if no changes
        """
        has_changes = False
        
        for field, value in new_data.items():
            # Skip base model fields that shouldn't be updated from external
            if field in ['id', 'entered_at', 'entered_by', 'last_modified_by']:
                continue
            
            # Skip the unique identifier field
            if hasattr(existing_record, field):
                current_value = getattr(existing_record, field)
                
                # Compare values (handle None cases)
                if current_value != value:
                    # Special handling for datetime comparisons
                    if isinstance(value, datetime) and isinstance(current_value, datetime):
                        if value.replace(microsecond=0) != current_value.replace(microsecond=0):
                            setattr(existing_record, field, value)
                            has_changes = True
                    else:
                        setattr(existing_record, field, value)
                        has_changes = True
        
        if has_changes:
            existing_record.last_modified_at = datetime.utcnow()
            # Keep entered_by and last_modified_by as 0 for sync operations
            if not existing_record.entered_by:
                existing_record.entered_by = 0
            existing_record.last_modified_by = 0
        
        return has_changes
    
    def _create_record(
        self,
        model_class: Any,
        data: Dict[str, Any],
        table_name: str
    ) -> Optional[Any]:
        """
        Create a new record from data dictionary.
        
        Args:
            model_class: SQLAlchemy model class
            data: Dictionary with record data
            table_name: Table name for logging
        
        Returns:
            New model instance or None if creation failed
        """
        try:
            # Remove fields that shouldn't be set from external data
            record_data = {k: v for k, v in data.items() 
                          if k not in ['id', 'entered_at', 'entered_by', 'last_modified_by', 'last_modified_at']}
            
            # Set base model fields before creating instance
            record_data['entered_at'] = datetime.utcnow()
            record_data['entered_by'] = 0  # System sync
            record_data['last_modified_at'] = datetime.utcnow()
            record_data['last_modified_by'] = 0  # System sync
            record_data['is_archived'] = False
            
            # Create new instance
            new_record = model_class(**record_data)
            
            return new_record
        
        except Exception as e:
            logger.error(f"Failed to create record in {table_name}: {str(e)}")
            return None

