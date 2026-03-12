"""
Stage 2 Sync: rb9_db → new_gls_db
"""

from datetime import datetime
from typing import Dict, Any, Optional, Type
from sqlalchemy.orm import Session

from src.core.logger import logger
from src.core.rb9_database import Rb9DatabaseConnection
from src.core.database import SessionLocal
from src.core.timezone_utils import get_timezone_now
from src.core.sync.synchronization_configuration import get_sync_order, get_table_config_stage2
from src.core.sync.resource_onboarding_synchronization_service import ResourceOnboardingSynchronizationService
from src.core.sync.validation_utils import validate_date_range, normalize_string
from src.resources.models import Resources
from src.cases.models import Cases
from src.billings.models import Billings
from src.jobs_tasks.models import JobsTasks
from src.jobs.models import Jobs
from src.witnesses.models import Witnesses
from src.witness_videos.models import WitnessVideos
from src.additional_documents.models import AdditionalDocuments
from src.equipment_time.models import EquipmentTime



class Rb9ToNewGlsSynchronizationService:
    
    # Table-specific fields that should never be updated during sync
    TABLE_UPDATE_EXCLUDE_FIELDS = {
        'Cases': ['case_number', 'case_short_name', 'entered_at', 'entered_by', 'last_modified_at', 'last_modified_by'],
        'Resources': ['login_password', 'entered_at', 'entered_by', 'last_modified_at', 'last_modified_by'],
        'Jobs': ['entered_at', 'entered_by', 'last_modified_at', 'last_modified_by'],
        'JobsTasks': ['entered_at', 'entered_by', 'last_modified_at', 'last_modified_by']
    }
    
    FOREIGN_KEY_VALIDATIONS = {
        'Jobs': {
            'case_no': ('Cases', 'case_no')
        },
        'JobsTasks': {
            'job_no': ('Jobs', 'job_no'),
            'rsrc_no': ('Resources', 'rsrc_no') 
        }
    }   
    
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
            # Use the already imported models from the top of the file
            model_map = {
                'Resources': Resources,
                'Cases': Cases,
                'Jobs': Jobs,
                'JobsTasks': JobsTasks,
                'Billings': Billings,
                'Witnesses': Witnesses,
                'WitnessVideos': WitnessVideos,
                'AdditionalDocuments': AdditionalDocuments,
                'EquipmentTime': EquipmentTime,
            }
            
            if model_class_name in model_map:
                return model_map[model_class_name]
            else:
                logger.warning(f"Unknown model class: {model_class_name}")
                return None
        except Exception as e:
            logger.error(f"Failed to resolve model {model_class_name}: {str(e)}")
            return None
    
    def _transform_field_names(self, rb9_record: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        mapped_record = {}
        for rb9_field, new_gls_field in field_mapping.items():
            if rb9_field in rb9_record:
                value = rb9_record[rb9_field]
                # Normalize string values (trim whitespace, empty to None)
                if isinstance(value, str):
                    value = normalize_string(value)
                mapped_record[new_gls_field] = value
        return mapped_record
    
    def _find_existing_record(self, db: Session, model_class: Type, unique_field: str, unique_value: Any):
        return db.query(model_class).filter(getattr(model_class, unique_field) == unique_value).first()
    
    def _validate_foreign_keys(
        self,
        db: Session,
        table_name: str,
        mapped_record: Dict[str, Any],
        model_class: Type
    ) -> tuple:
        """
        Validate foreign key relationships before insert/update.
        
        Returns:
            (is_valid, error_message) - True if all FKs are valid, False with error message otherwise
        """
        if table_name not in self.FOREIGN_KEY_VALIDATIONS:
            return True, None
        
        fk_validations = self.FOREIGN_KEY_VALIDATIONS[table_name]
        
        for field_name, (related_table, related_field) in fk_validations.items():
            # Check if this field is in the mapped record
            if field_name not in mapped_record:
                continue
            
            fk_value = mapped_record[field_name]
            
            # Skip validation if value is None (nullable foreign keys)
            if fk_value is None:
                continue
            
            # Resolve the related model class
            related_model = self._resolve_model_class(related_table)
            if not related_model:
                logger.warning(
                    f"[VALIDATION] Cannot validate FK {field_name} for {table_name}: "
                    f"Related model {related_table} not found"
                )
                continue
            
            # Check if the related record exists
            related_record = db.query(related_model).filter(
                getattr(related_model, related_field) == fk_value
            ).first()
            
            if not related_record:
                error_msg = (
                    f"Foreign key validation failed: {table_name}.{field_name}={fk_value} "
                    f"does not exist in {related_table}.{related_field}"
                )
                logger.warning(f"[VALIDATION] {error_msg}")
                return False, error_msg
        
        return True, None
    
    def _detect_field_changes(
        self,
        existing_record: Any,
        mapped_record: Dict[str, Any],
        exclude_fields: list = None,
        table_name: str = None
    ) -> Dict[str, Any]:
        exclude_fields = exclude_fields or []
        
        # Add table-specific exclusions
        if table_name and table_name in self.TABLE_UPDATE_EXCLUDE_FIELDS:
            exclude_fields.extend(self.TABLE_UPDATE_EXCLUDE_FIELDS[table_name])
        
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
        limit: Optional[int] = None,
        batch_size: int = 1000,
        use_bulk_ops: bool = True
    ) -> Dict[str, int]:
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Validate date range
        is_valid, date_error = validate_date_range(start_date, end_date)
        if not is_valid:
            logger.error(f"[VALIDATION] {date_error}. Sync aborted for {table_name}.")
            self.stats['errors'] = 1
            return self.stats
        
        if table_name == 'Resources':
            users_service = ResourceOnboardingSynchronizationService(self.rb9_db)
            return users_service.synchronize_resources(start_date=start_date, end_date=end_date, limit=limit)
        
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
            table_start_time = datetime.utcnow()
            logger.info(f"Starting Stage 1 sync for {table_name} (batch_size={batch_size}, bulk_ops={use_bulk_ops})")
            
            # Build base query with filters
            params = {}
            where_clauses = []
            date_field_qualified = f'{date_field_table_alias}."{date_field}"' if date_field_table_alias else f'"{date_field}"'
            
            if start_date:
                where_clauses.append(f'{date_field_qualified} >= :start_date')
                params['start_date'] = start_date
            
            if end_date:
                where_clauses.append(f'{date_field_qualified} <= :end_date')
                params['end_date'] = end_date

            # Build base query
            base_query = query
            if where_clauses:
                where_clause = " AND ".join(where_clauses)
                if 'WHERE' in base_query.upper():
                    base_query += f" AND {where_clause}"
                else:
                    base_query += f" WHERE {where_clause}"
            
            # Add ORDER BY for consistent pagination
            if 'ORDER BY' not in base_query.upper():
                base_query += f" ORDER BY {date_field_qualified}"
            
            # Pagination-based processing
            offset = 0
            total_processed = 0
            batch_num = 0
            
            db: Session = SessionLocal()
            try:
                while True:
                    batch_num += 1
                    
                    # Build paginated query
                    paginated_query = base_query
                    if limit:
                        # If limit specified, calculate remaining records
                        remaining = limit - total_processed
                        if remaining <= 0:
                            break
                        paginated_query += f" LIMIT {min(batch_size, remaining)} OFFSET {offset}"
                    else:
                        paginated_query += f" LIMIT {batch_size} OFFSET {offset}"
                    
                    try:
                        logger.info(
                            f"Fetching batch {batch_num} for {table_name}: "
                            f"offset={offset}, limit={batch_size} (total processed: {total_processed})"
                        )
                        logger.debug(f"Query: {paginated_query[:200]}...")
                        
                        rb9_records = self.rb9_db.execute_query(paginated_query, params)
                        
                        if not rb9_records:
                            logger.info(f"No more {table_name} records to sync. Total processed: {total_processed}")
                            break
                        
                        logger.info(f"Fetched {len(rb9_records)} {table_name} records in batch {batch_num}")
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch {table_name} batch {batch_num}: {str(e)}", exc_info=True)
                        self.stats['errors'] += 1
                        break
                    
                    # Process batch
                    if use_bulk_ops:
                        batch_result = self._process_batch_bulk(
                            db, table_name, rb9_records, model_class, unique_field, 
                            new_gls_unique_field, field_mapping
                        )
                    else:
                        batch_result = self._process_batch_individual(
                            db, table_name, rb9_records, model_class, unique_field,
                            new_gls_unique_field, field_mapping
                        )
                    
                    # Update stats
                    self.stats['inserted'] += batch_result['inserted']
                    self.stats['updated'] += batch_result['updated']
                    self.stats['errors'] += batch_result['errors']
                    self.stats['skipped'] += batch_result['skipped']
                    
                    total_processed += len(rb9_records)
                    offset += batch_size
                    
                    # Log progress every 10 batches or every 10k records for large datasets
                    if batch_num % 10 == 0 or total_processed % 10000 == 0:
                        elapsed_time = (datetime.utcnow() - table_start_time).total_seconds()
                        records_per_sec = total_processed / elapsed_time if elapsed_time > 0 else 0
                        estimated_remaining = "N/A"
                        if limit and records_per_sec > 0:
                            remaining = limit - total_processed
                            estimated_remaining = f"{remaining / records_per_sec:.0f}s" if remaining > 0 else "0s"
                        
                        logger.info(
                            f"[PROGRESS] {table_name} - Batch {batch_num}: "
                            f"Processed {total_processed:,} records in {elapsed_time:.0f}s "
                            f"({records_per_sec:.1f} records/sec). "
                            f"Est. remaining: {estimated_remaining}. "
                            f"Total: Inserted={self.stats['inserted']}, Updated={self.stats['updated']}, "
                            f"Errors={self.stats['errors']}, Skipped={self.stats['skipped']}"
                        )
                    else:
                        logger.debug(
                            f"Batch {batch_num} completed: "
                            f"Inserted={batch_result['inserted']}, Updated={batch_result['updated']}, "
                            f"Errors={batch_result['errors']}, Skipped={batch_result['skipped']}. "
                            f"Total processed: {total_processed}"
                        )
                    
                    # Check if we've reached the limit
                    if limit and total_processed >= limit:
                        logger.info(f"Reached limit of {limit} records for {table_name}")
                        break
                
            finally:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Error closing database session: {str(close_error)}")
            
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
            try:
                if 'db' in locals():
                    db.close()
            except Exception:
                pass
        
        return self.stats
    
    def _process_batch_bulk(
        self,
        db: Session,
        table_name: str,
        rb9_records: list,
        model_class: Type,
        unique_field: str,
        new_gls_unique_field: str,
        field_mapping: Dict[str, str]
    ) -> Dict[str, int]:
    
        batch_stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        try:
            new_records = []
            update_records = []
            
            # First pass: Transform and check existing records
            for rb9_record in rb9_records:
                unique_value = rb9_record.get(unique_field)
                if not unique_value:
                    batch_stats['skipped'] += 1
                    continue
                
                mapped_record = self._transform_field_names(rb9_record, field_mapping)
                existing_record = self._find_existing_record(db, model_class, new_gls_unique_field, unique_value)
                
                if existing_record:
                    changes = self._detect_field_changes(existing_record, mapped_record, table_name=table_name)
                    if changes:
                        # Validate FK if needed
                        if table_name in self.FOREIGN_KEY_VALIDATIONS:
                            fk_fields_updated = [f for f in changes.keys() if f in self.FOREIGN_KEY_VALIDATIONS[table_name]]
                            if fk_fields_updated:
                                temp_mapped = mapped_record.copy()
                                for field in fk_fields_updated:
                                    temp_mapped[field] = changes[field]
                                is_valid, fk_error = self._validate_foreign_keys(db, table_name, temp_mapped, model_class)
                                if not is_valid:
                                    batch_stats['skipped'] += 1
                                    continue
                        
                        # Prepare update dict
                        update_dict = {'id': existing_record.id}
                        table_exclude_fields = self.TABLE_UPDATE_EXCLUDE_FIELDS.get(table_name, [])
                        
                        for field, value in changes.items():
                            if field not in table_exclude_fields and hasattr(existing_record, field):
                                update_dict[field] = value
                        
                        if hasattr(existing_record, 'last_modified_at'):
                            update_dict['last_modified_at'] = get_timezone_now()
                        
                        update_records.append(update_dict)
                else:
                    # Validate FK for new records
                    if table_name in self.FOREIGN_KEY_VALIDATIONS:
                        is_valid, fk_error = self._validate_foreign_keys(db, table_name, mapped_record, model_class)
                        if not is_valid:
                            batch_stats['skipped'] += 1
                            continue
                    
                    # Prepare insert dict
                    insert_dict = {}
                    for field, value in mapped_record.items():
                        if hasattr(model_class, field):
                            insert_dict[field] = value
                    
                    if 'entered_by' not in insert_dict:
                        insert_dict['entered_by'] = 0
                    if 'last_modified_by' not in insert_dict:
                        insert_dict['last_modified_by'] = 0
                    if 'entered_at' not in insert_dict:
                        insert_dict['entered_at'] = get_timezone_now()
                    if 'last_modified_at' not in insert_dict:
                        insert_dict['last_modified_at'] = get_timezone_now()
                    
                    new_records.append(insert_dict)
            
            # Bulk operations
            if new_records:
                try:
                    db.bulk_insert_mappings(model_class, new_records)
                    batch_stats['inserted'] = len(new_records)
                    logger.debug(f"Bulk inserted {len(new_records)} {table_name} records")
                except Exception as e:
                    logger.warning(f"Bulk insert failed for {table_name}, falling back to individual processing: {str(e)}")
                    db.rollback()
                    # Fallback to individual processing for new records
                    for insert_dict in new_records:
                        try:
                            new_record = model_class(**insert_dict)
                            db.add(new_record)
                            db.commit()
                            batch_stats['inserted'] += 1
                        except Exception as insert_error:
                            logger.error(f"Failed to insert {table_name} record: {str(insert_error)}")
                            db.rollback()
                            batch_stats['errors'] += 1
            
            if update_records:
                try:
                    db.bulk_update_mappings(model_class, update_records)
                    batch_stats['updated'] = len(update_records)
                    logger.debug(f"Bulk updated {len(update_records)} {table_name} records")
                except Exception as e:
                    logger.warning(f"Bulk update failed for {table_name}, falling back to individual processing: {str(e)}")
                    db.rollback()
                    # Fallback to individual processing for updates
                    for update_dict in update_records:
                        try:
                            record_id = update_dict.pop('id')
                            existing = db.query(model_class).filter(model_class.id == record_id).first()
                            if existing:
                                for field, value in update_dict.items():
                                    if hasattr(existing, field):
                                        setattr(existing, field, value)
                                db.commit()
                                batch_stats['updated'] += 1
                        except Exception as update_error:
                            logger.error(f"Failed to update {table_name} record: {str(update_error)}")
                            db.rollback()
                            batch_stats['errors'] += 1
            
            # Commit all bulk operations
            if new_records or update_records:
                db.commit()
            
        except Exception as e:
            logger.error(f"Error in bulk batch processing for {table_name}: {str(e)}", exc_info=True)
            db.rollback()
            batch_stats['errors'] += len(rb9_records)
        
        return batch_stats
    
    def _process_batch_individual(
        self,
        db: Session,
        table_name: str,
        rb9_records: list,
        model_class: Type,
        unique_field: str,
        new_gls_unique_field: str,
        field_mapping: Dict[str, str]
    ) -> Dict[str, int]:
        batch_stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        for rb9_record in rb9_records:
            savepoint = db.begin_nested()
            unique_value = None
            try:
                unique_value = rb9_record.get(unique_field)
                if not unique_value:
                    logger.warning(
                        f"[SKIP] {table_name} record missing {unique_field}. Record: {rb9_record}"
                    )
                    batch_stats['skipped'] += 1
                    savepoint.rollback()
                    continue
                
                mapped_record = self._transform_field_names(rb9_record, field_mapping)
                
                existing_record = self._find_existing_record(db, model_class, new_gls_unique_field, unique_value)
                
                if existing_record:
                    changes = self._detect_field_changes(existing_record, mapped_record, table_name=table_name)
                    if changes:
                        # Validate foreign key relationships if any FK fields are being updated
                        fk_fields_being_updated = []
                        if table_name in self.FOREIGN_KEY_VALIDATIONS:
                            fk_validations = self.FOREIGN_KEY_VALIDATIONS[table_name]
                            fk_fields_being_updated = [
                                field for field in changes.keys() 
                                if field in fk_validations
                            ]
                        
                        if fk_fields_being_updated:
                            temp_mapped = mapped_record.copy()
                            for field in fk_fields_being_updated:
                                temp_mapped[field] = changes[field]
                            
                            is_valid, fk_error = self._validate_foreign_keys(
                                db, table_name, temp_mapped, model_class
                            )
                            
                            if not is_valid:
                                logger.warning(
                                    f"[SKIP] {table_name} record {new_gls_unique_field}={unique_value} update skipped "
                                    f"due to FK validation: {fk_error}"
                                )
                                batch_stats['skipped'] += 1
                                savepoint.rollback()
                                continue
                        
                        changed_fields = []
                        table_exclude_fields = self.TABLE_UPDATE_EXCLUDE_FIELDS.get(table_name, [])
                        
                        for field, value in changes.items():
                            if field in table_exclude_fields:
                                logger.debug(
                                    f"[SKIP] Field '{field}' excluded from update for {table_name} record {unique_value}"
                                )
                                continue
                            if hasattr(existing_record, field):
                                old_value = getattr(existing_record, field, None)
                                setattr(existing_record, field, value)
                                changed_fields.append(f"{field}: {old_value} -> {value}")
                        
                        if hasattr(existing_record, 'last_modified_at'):
                            existing_record.last_modified_at = get_timezone_now()
                        
                        savepoint.commit()
                        db.commit()
                        db.refresh(existing_record)
                        
                        batch_stats['updated'] += 1
                        logger.debug(
                            f"[SUCCESS] Updated {table_name} record {new_gls_unique_field}={unique_value}. "
                            f"Changed fields: {', '.join(changed_fields)}"
                        )
                    else:
                        batch_stats['skipped'] += 1
                        savepoint.rollback()
                        logger.debug(f"[SKIP] No changes for {table_name} record {new_gls_unique_field}={unique_value}")
                else:
                    # Validate foreign key relationships before creating new record
                    is_valid, fk_error = self._validate_foreign_keys(
                        db, table_name, mapped_record, model_class
                    )
                    
                    if not is_valid:
                        logger.warning(
                            f"[SKIP] {table_name} record {new_gls_unique_field}={unique_value} skipped due to FK validation: {fk_error}"
                        )
                        batch_stats['skipped'] += 1
                        savepoint.rollback()
                        continue
                    
                    model_kwargs = {}
                    for field, value in mapped_record.items():
                        if hasattr(model_class, field):
                            model_kwargs[field] = value
                    
                    if 'entered_by' not in model_kwargs:
                        model_kwargs['entered_by'] = 0
                    if 'last_modified_by' not in model_kwargs:
                        model_kwargs['last_modified_by'] = 0
                    if 'entered_at' not in model_kwargs:
                        model_kwargs['entered_at'] = get_timezone_now()
                    if 'last_modified_at' not in model_kwargs:
                        model_kwargs['last_modified_at'] = get_timezone_now()
                    
                    try:
                        new_record = model_class(**model_kwargs)
                        db.add(new_record)
                        savepoint.commit()
                        db.commit()
                        db.refresh(new_record)
                        
                        batch_stats['inserted'] += 1
                        logger.debug(
                            f"[SUCCESS] Created new {table_name} record {new_gls_unique_field}={unique_value}"
                        )
                    except Exception as create_error:
                        error_msg = str(create_error)
                        if 'foreign key' in error_msg.lower() or 'constraint' in error_msg.lower():
                            logger.error(
                                f"[ERROR] Foreign key constraint violation creating {table_name} record "
                                f"{new_gls_unique_field}={unique_value}: {error_msg}"
                            )
                        else:
                            logger.error(
                                f"[ERROR] Failed to create {table_name} record {new_gls_unique_field}={unique_value}: {error_msg}"
                            )
                        batch_stats['errors'] += 1
                        savepoint.rollback()
                        continue
            
            except Exception as e:
                error_msg = (
                    f"[ERROR] Failed to process {table_name} record {new_gls_unique_field}={unique_value}: {str(e)}. "
                    f"Rolling back transaction for this record only."
                )
                logger.error(error_msg, exc_info=True)
                batch_stats['errors'] += 1
                
                try:
                    savepoint.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback savepoint: {str(rollback_error)}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
                continue
        
        return batch_stats
    
    def synchronize_all_tables(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        batch_size: int = 1000,
        use_bulk_ops: bool = True
    ) -> Dict[str, Any]:
        sync_order = get_sync_order()
        
        stage_1_tables = []
        for table_name in sync_order:
            config_data = get_table_config_stage2(table_name)
            if config_data and config_data.get('model_class') is not None:
                stage_1_tables.append(table_name)
        
        results = {}
        
        logger.info(f"Starting Stage 1 sync for tables: {stage_1_tables}")
        logger.info(f"Note: Lists and Timezones are skipped (used only for JOINs in Cases/Jobs queries)")
        logger.info("=" * 60)
        logger.info("IMPORTANT: Tables sync SEQUENTIALLY (one at a time)")
        logger.info("Each table must complete ALL records before next table starts")
        logger.info("=" * 60)
        
        for idx, table_name in enumerate(stage_1_tables, 1):
            logger.info("")
            logger.info(f"[{idx}/{len(stage_1_tables)}] Starting sync for table: {table_name}")
            logger.info(f"Waiting for {table_name} to complete before moving to next table...")
            
            try:
                table_stats = self.synchronize_table(
                    table_name=table_name,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    batch_size=batch_size,
                    use_bulk_ops=use_bulk_ops
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
            f"Stage 1 sync completed for all tables: "
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

