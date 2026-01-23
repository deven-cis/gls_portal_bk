"""
Stage 2 Sync: rb9_db → new_gls_db
"""

from datetime import datetime
from typing import Dict, Any, Optional, Type
from sqlalchemy.orm import Session

from src.core.logger import logger
from src.core.rb9_database import Rb9DatabaseConnection
from src.core.database import SessionLocal
from src.core.sync.synchronization_configuration import get_sync_order, get_table_config_stage2
from src.core.sync.user_onboarding_synchronization_service import UserOnboardingSynchronizationService


class Rb9ToNewGlsSynchronizationService:

    
    def __init__(self, rb9_db: Optional[Rb9DatabaseConnection] = None):
        self.rb9_db = rb9_db or Rb9DatabaseConnection()
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def _resolve_model_class(self, model_class_name: str):
        try:
            if model_class_name == 'Users':
                from src.users.models import Users
                return Users
            elif model_class_name == 'Cases':
                from src.cases.models import Cases
                return Cases
            elif model_class_name == 'Jobs':
                from src.jobs.models import Jobs
                return Jobs
            else:
                logger.warning(f"Unknown model class: {model_class_name}")
                return None
        except ImportError as e:
            logger.error(f"Failed to import model {model_class_name}: {str(e)}")
            return None
    
    def _transform_field_names(self, rb9_record: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        mapped_record = {}
        for rb9_field, new_gls_field in field_mapping.items():
            if rb9_field in rb9_record:
                mapped_record[new_gls_field] = rb9_record[rb9_field]
        return mapped_record
    
    def _find_existing_record(self, db: Session, model_class: Type, unique_field: str, unique_value: Any):
        return db.query(model_class).filter(getattr(model_class, unique_field) == unique_value).first()
    
    def _detect_field_changes(
        self,
        existing_record: Any,
        mapped_record: Dict[str, Any],
        exclude_fields: list = None
    ) -> Dict[str, Any]:
        exclude_fields = exclude_fields or []
        exclude_fields.extend(['id', 'entered_at', 'entered_by', 'last_modified_at', 'last_modified_by', 'is_archived'])
        
        changes = {}
        for field, new_value in mapped_record.items():
            if field in exclude_fields:
                continue
            
            if not hasattr(existing_record, field):
                continue
            
            existing_value = getattr(existing_record, field, None)

            if existing_value != new_value:
                if existing_value is None and new_value is None:
                    continue
                if existing_value is None or new_value is None:
                    changes[field] = new_value
                else:
                    if str(existing_value) != str(new_value):
                        changes[field] = new_value
        
        return changes
    
    def synchronize_table(
        self,
        table_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        if table_name == 'Users':
            users_service = UserOnboardingSynchronizationService(self.rb9_db)
            return users_service.synchronize_users(start_date=start_date, end_date=end_date, limit=limit)
        
        config_data = get_table_config_stage2(table_name)
        if not config_data:
            logger.error(f"No configuration found for table: {table_name}")
            self.stats['errors'] = 1
            return self.stats
        
        model_class_name = config_data.get('model_class')
        if model_class_name is None:
            logger.info(f"Skipping {table_name} - no model class in new_gls_db")
            return self.stats
        
        model_class = self._resolve_model_class(model_class_name)
        if model_class is None:
            logger.error(f"Failed to get model class for {table_name}")
            self.stats['errors'] = 1
            return self.stats
        
        unique_field = config_data['rb9_unique_field']
        new_gls_unique_field = config_data['unique_field']
        query = config_data['query']
        date_field = config_data['date_field']
        field_mapping = config_data['field_mapping']
        date_field_table_alias = config_data.get('date_field_table_alias')
        
        try:
            logger.info(f"Starting Stage 2 sync for {table_name}")
            
            params = {}
            where_clauses = []
            
            try:
                date_field_qualified = f'{date_field_table_alias}."{date_field}"' if date_field_table_alias else f'"{date_field}"'
            
                if start_date:
                    where_clauses.append(f'{date_field_qualified} >= :start_date')
                    params['start_date'] = start_date
                
                if end_date:
                    where_clauses.append(f'{date_field_qualified} <= :end_date')
                    params['end_date'] = end_date

                if where_clauses:
                    where_clause = " AND ".join(where_clauses)
                    if 'WHERE' in query.upper():
                        query += f" AND {where_clause}"
                    else:
                        query += f" WHERE {where_clause}"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                logger.info(f"Fetching {table_name} from rb9_db...")
                logger.debug(f"Query: {query[:200]}...")
                
                rb9_records = self.rb9_db.execute_query(query, params)
                logger.info(f"Fetched {len(rb9_records)} {table_name} records from rb9_db")
            except Exception as e:
                logger.error(f"Failed to fetch {table_name} records from rb9_db: {str(e)}", exc_info=True)
                self.stats['errors'] += 1
                return self.stats
            
            if not rb9_records:
                logger.info(f"No {table_name} records to sync")
                return self.stats
            
            db: Session = SessionLocal()
            try:
                for rb9_record in rb9_records:
                    try:
                        unique_value = rb9_record.get(unique_field)
                        if not unique_value:
                            logger.warning(f"Skipping {table_name} record - missing {unique_field}")
                            self.stats['skipped'] += 1
                            continue
                        
                        mapped_record = self._transform_field_names(rb9_record, field_mapping)
                        
                        existing_record = self._find_existing_record(db, model_class, new_gls_unique_field, unique_value)
                        
                        if existing_record:
                            changes = self._detect_field_changes(existing_record, mapped_record)
                            if changes:
                                for field, value in changes.items():
                                    if hasattr(existing_record, field):
                                        setattr(existing_record, field, value)
                                
                                if hasattr(existing_record, 'last_modified_at'):
                                    existing_record.last_modified_at = datetime.utcnow()
                                
                                db.commit()
                                db.refresh(existing_record)
                                
                                self.stats['updated'] += 1
                                logger.debug(f"Updated {table_name} record with {new_gls_unique_field}={unique_value}")
                            else:
                                self.stats['skipped'] += 1
                                logger.debug(f"No changes for {table_name} record with {new_gls_unique_field}={unique_value}, skipping")
                        else:
                            model_kwargs = {}
                            for field, value in mapped_record.items():
                                if hasattr(model_class, field):
                                    model_kwargs[field] = value
                            
                            if 'entered_by' not in model_kwargs:
                                model_kwargs['entered_by'] = 0
                            if 'last_modified_by' not in model_kwargs:
                                model_kwargs['last_modified_by'] = 0
                            
                            new_record = model_class(**model_kwargs)
                            
                            db.add(new_record)
                            db.commit()
                            db.refresh(new_record)
                            
                            self.stats['inserted'] += 1
                            logger.info(f"Created new {table_name} record with {new_gls_unique_field}={unique_value}")
                    
                    except Exception as e:
                        logger.error(
                            f"Error processing {table_name} record with {new_gls_unique_field}={unique_value}: {str(e)}",
                            exc_info=True
                        )
                        self.stats['errors'] += 1
                        try:
                            db.rollback()
                        except Exception as rollback_error:
                            logger.error(f"Failed to rollback transaction: {str(rollback_error)}")
                        continue
                
            finally:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Error closing database session: {str(close_error)}")
            
            logger.info(
                f"Stage 2 sync completed for {table_name}: "
                f"Inserted={self.stats['inserted']}, "
                f"Updated={self.stats['updated']}, "
                f"Errors={self.stats['errors']}, "
                f"Skipped={self.stats['skipped']}"
            )
        
        except Exception as e:
            logger.error(f"Failed to sync {table_name} in Stage 2: {str(e)}", exc_info=True)
            self.stats['errors'] += 1
            try:
                if 'db' in locals():
                    db.close()
            except Exception:
                pass
        
        return self.stats
    
    def synchronize_all_tables(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        sync_order = get_sync_order()
        
        stage2_tables = []
        for table_name in sync_order:
            config_data = get_table_config_stage2(table_name)
            if config_data and config_data.get('model_class') is not None:
                stage2_tables.append(table_name)
        
        results = {}
        
        logger.info(f"Starting Stage 2 sync for tables: {stage2_tables}")
        logger.info(f"Note: Lists and Timezones are skipped (used only for JOINs in Cases/Jobs queries)")
        logger.info("=" * 60)
        logger.info("IMPORTANT: Tables sync SEQUENTIALLY (one at a time)")
        logger.info("Each table must complete ALL records before next table starts")
        logger.info("=" * 60)
        
        for idx, table_name in enumerate(stage2_tables, 1):
            logger.info("")
            logger.info(f"[{idx}/{len(stage2_tables)}] Starting sync for table: {table_name}")
            logger.info(f"Waiting for {table_name} to complete before moving to next table...")
            
            try:
                table_stats = self.synchronize_table(
                    table_name=table_name,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                results[table_name] = table_stats
                
                logger.info(f"{table_name} sync completed: Inserted={table_stats.get('inserted', 0)}, "
                          f"Updated={table_stats.get('updated', 0)}, Errors={table_stats.get('errors', 0)}")
                
            except Exception as e:
                logger.error(f"Failed to sync {table_name}: {str(e)}", exc_info=True)
                results[table_name] = {'error': str(e)}
            
            logger.info(f"Moving to next table in dependency order...")
        
        total_inserted = sum(r.get('inserted', 0) for r in results.values())
        total_updated = sum(r.get('updated', 0) for r in results.values())
        total_errors = sum(r.get('errors', 0) for r in results.values())
        total_emails = sum(r.get('emails_sent', 0) for r in results.values())
        
        logger.info(
            f"Stage 2 sync completed for all tables: "
            f"Total Inserted={total_inserted}, "
            f"Total Updated={total_updated}, "
            f"Total Errors={total_errors}, "
            f"Total Emails Sent={total_emails}"
        )
        
        return {
            'tables': results,
            'total_inserted': total_inserted,
            'total_updated': total_updated,
            'total_errors': total_errors,
            'total_emails_sent': total_emails
        }

