"""
Stage 1 Sync: External DB → rb9_db
Syncs data from external_db to rb9_db using raw SQL queries.
Processes tables in dependency order with CreateAtRb/UpdateAtRb tracking.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from src.core.logger import logger
from src.core.sync.external_database_connection import ExternalDatabaseConnection
from src.core.rb9_database import Rb9DatabaseConnection
from src.core.sync.synchronization_configuration import get_sync_order, get_table_config_stage1


class ExternalToRb9SynchronizationService:
    """
    Service for synchronizing data from External DB to rb9_db.
    Uses raw SQL queries and tracks CreateAtRb/UpdateAtRb timestamps.
    """
    
    def __init__(self, external_db: Optional[ExternalDatabaseConnection] = None, rb9_db: Optional[Rb9DatabaseConnection] = None):
        self.external_db = external_db or ExternalDatabaseConnection()
        self.rb9_db = rb9_db or Rb9DatabaseConnection()
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def sync_table(
        self,
        table_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Sync a single table from External DB to rb9_db.
        
        Args:
            table_name: Table name (must be in SYNC_ORDER)
            start_date: Start date for LastModified filter (for testing, use static date)
            end_date: End date for LastModified filter
            limit: Limit number of records (for testing: 2)
        
        Returns:
            Dictionary with sync statistics
        """
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Get table configuration
        config = get_table_config_stage1(table_name)
        if not config:
            logger.error(f"No configuration found for table: {table_name}")
            self.stats['errors'] = 1
            return self.stats
        
        unique_field = config['unique_field']
        query = config['query']
        date_field = config['date_field']
        exclude_fields = config.get('exclude_fields', [])
        
        try:
            logger.info(f"Starting Stage 1 sync for {table_name}")
            
            # Build query with date filter
            params = {}
            where_clauses = []
            
            if start_date:
                where_clauses.append(f'"{date_field}" >= :start_date')
                params['start_date'] = start_date
            
            if end_date:
                where_clauses.append(f'"{date_field}" <= :end_date')
                params['end_date'] = end_date
            
            if where_clauses:
                where_clause = " AND ".join(where_clauses)
                if 'WHERE' in query.upper():
                    query += f" AND {where_clause}"
                else:
                    query += f" WHERE {where_clause}"
            
            # Add LIMIT for testing
            if limit:
                query += f" LIMIT {limit}"
            
            logger.info(f"Fetching records from External DB for {table_name}...")
            logger.info(f"Query: {query[:200]}...")  # Log first 200 chars
            
            # Fetch records from External DB
            external_records = self.external_db.execute_query(query, params)
            logger.info(f"Fetched {len(external_records)} records from External DB")
            
            if not external_records:
                logger.info(f"No records to sync for {table_name}")
                return self.stats
            
            # Process each record
            for record in external_records:
                try:
                    unique_value = record.get(unique_field)
                    if not unique_value:
                        logger.warning(f"Skipping record in {table_name} - missing {unique_field}")
                        self.stats['skipped'] += 1
                        continue
                    
                    # Check if record exists BEFORE upsert
                    existed_before = self.rb9_db.check_record_exists(config['table_name'], unique_field, unique_value)
                    
                    # Upsert record with tracking
                    result = self.rb9_db.execute_upsert(
                        table_name=config['table_name'],
                        record=record,
                        unique_field=unique_field,
                        exclude_fields=exclude_fields
                    )
                    
                    if result:
                        # Track insert or update based on whether it existed before
                        if existed_before:
                            self.stats['updated'] += 1
                        else:
                            self.stats['inserted'] += 1
                    else:
                        self.stats['skipped'] += 1
                    
                    # Commit in batches
                    if (self.stats['inserted'] + self.stats['updated']) % 10 == 0:
                        logger.debug(f"Processed {self.stats['inserted'] + self.stats['updated']} records for {table_name}")
                
                except Exception as e:
                    logger.error(f"Error processing record in {table_name}: {str(e)}", exc_info=True)
                    self.stats['errors'] += 1
                    continue
            
            logger.info(
                f"Stage 1 sync completed for {table_name}: "
                f"Inserted={self.stats['inserted']}, "
                f"Updated={self.stats['updated']}, "
                f"Errors={self.stats['errors']}, "
                f"Skipped={self.stats['skipped']}"
            )
        
        except Exception as e:
            logger.error(f"Failed to sync {table_name} in Stage 1: {str(e)}", exc_info=True)
            self.stats['errors'] += 1
        
        return self.stats
    
    def sync_all(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sync all tables in dependency order.
        
        Args:
            start_date: Start date for LastModified filter
            end_date: End date for LastModified filter
            limit: Limit records per table (for testing: 2)
        
        Returns:
            Dictionary with results for each table
        """
        sync_order = get_sync_order()
        results = {}
        
        logger.info(f"Starting Stage 1 sync for all tables in dependency order: {sync_order}")
        logger.info("=" * 60)
        logger.info("IMPORTANT: Tables sync SEQUENTIALLY (one at a time)")
        logger.info("Each table must complete ALL records before next table starts")
        logger.info("=" * 60)
        
        for idx, table_name in enumerate(sync_order, 1):
            logger.info("")
            logger.info(f"[{idx}/{len(sync_order)}] Starting sync for table: {table_name}")
            logger.info(f"Waiting for {table_name} to complete before moving to next table...")
            
            try:
                table_stats = self.sync_table(
                    table_name=table_name,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                results[table_name] = table_stats
                
                logger.info(f"✓ {table_name} sync completed: Inserted={table_stats.get('inserted', 0)}, "
                          f"Updated={table_stats.get('updated', 0)}, Errors={table_stats.get('errors', 0)}")
                
            except Exception as e:
                logger.error(f"✗ Failed to sync {table_name}: {str(e)}", exc_info=True)
                results[table_name] = {'error': str(e)}
            
            logger.info(f"Moving to next table in dependency order...")
        
        # Calculate totals
        total_inserted = sum(r.get('inserted', 0) for r in results.values())
        total_updated = sum(r.get('updated', 0) for r in results.values())
        total_errors = sum(r.get('errors', 0) for r in results.values())
        
        logger.info(
            f"Stage 1 sync completed for all tables: "
            f"Total Inserted={total_inserted}, "
            f"Total Updated={total_updated}, "
            f"Total Errors={total_errors}"
        )
        
        return {
            'tables': results,
            'total_inserted': total_inserted,
            'total_updated': total_updated,
            'total_errors': total_errors
        }

