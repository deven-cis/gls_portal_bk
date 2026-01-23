"""
Stage 2 Users Sync: rb9_db → new_gls_db
Syncs Users from rb9_db to new_gls_db with field mapping, password generation, and welcome emails.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from src.core.logger import logger
from src.core.rb9_database import Rb9DatabaseConnection
from src.core.database import SessionLocal
from src.core.sync.synchronization_configuration import get_table_config_stage2
from src.users.models import Users
from src.users.utils import hash_password
from src.core.sync.email_service import generate_temporary_password, send_user_welcome_notification


class UserOnboardingSynchronizationService:
    
    def __init__(self, rb9_db: Optional[Rb9DatabaseConnection] = None):
        self.rb9_db = rb9_db or Rb9DatabaseConnection()
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'emails_sent': 0
        }
    
    def _transform_field_names(self, rb9_record: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        mapped_record = {}
        for rb9_field, new_gls_field in field_mapping.items():
            if rb9_field in rb9_record:
                mapped_record[new_gls_field] = rb9_record[rb9_field]
        return mapped_record
    
    def _find_existing_user(self, db: Session, user_no: int) -> Optional[Users]:
        return db.query(Users).filter(Users.user_no == user_no).first()
    
    def _detect_field_changes(
        self,
        existing_user: Users,
        mapped_record: Dict[str, Any],
        exclude_fields: list = None
    ) -> Dict[str, Any]:
        exclude_fields = exclude_fields or []
        exclude_fields.extend(['id', 'entered_at', 'entered_by', 'last_modified_at', 'last_modified_by', 'is_archived', 'login_password'])
        
        changes = {}
        for field, new_value in mapped_record.items():
            if field in exclude_fields:
                continue
            
            existing_value = getattr(existing_user, field, None)
            
            if existing_value != new_value:
                if existing_value is None and new_value is None:
                    continue
                if existing_value is None or new_value is None:
                    changes[field] = new_value
                else:
                    if str(existing_value) != str(new_value):
                        changes[field] = new_value
        
        return changes
    
    def synchronize_users(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0, 'emails_sent': 0}
        
        config_data = get_table_config_stage2('Users')
        if not config_data:
            logger.error("No configuration found for Users table in Stage 2")
            self.stats['errors'] = 1
            return self.stats
        
        unique_field = config_data['rb9_unique_field']
        query = config_data['query']
        date_field = config_data['date_field']
        field_mapping = config_data['field_mapping']
        
        try:
            logger.info("Starting Stage 2 Users sync from rb9_db to new_gls_db")
            
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
            
            if limit:
                query += f" LIMIT {limit}"
            
            logger.info(f"Fetching Users from rb9_db...")
            logger.debug(f"Query: {query[:200]}...")
            
            rb9_records = self.rb9_db.execute_query(query, params)
            logger.info(f"Fetched {len(rb9_records)} Users from rb9_db")
            
            if not rb9_records:
                logger.info("No Users to sync")
                return self.stats
            
            db: Session = SessionLocal()
            try:
                for rb9_record in rb9_records:
                    try:
                        user_no = rb9_record.get(unique_field)
                        if not user_no:
                            logger.warning(f"Skipping User record - missing {unique_field}")
                            self.stats['skipped'] += 1
                            continue
                        
                        mapped_record = self._transform_field_names(rb9_record, field_mapping)
                        
                        existing_user = self._find_existing_user(db, user_no)
                        
                        if existing_user:
                            changes = self._detect_field_changes(existing_user, mapped_record)
                            
                            if changes:
                                for field, value in changes.items():
                                    if field == 'login_password':
                                        continue
                                    if hasattr(existing_user, field):
                                        setattr(existing_user, field, value)
                                
                                existing_user.last_modified_at = datetime.utcnow()
                                
                                db.commit()
                                db.refresh(existing_user)
                                
                                self.stats['updated'] += 1
                                logger.debug(f"Updated User with user_no={user_no}")
                            else:
                                self.stats['skipped'] += 1
                                logger.debug(f"No changes for User with user_no={user_no}, skipping")
                        else:
                            temp_password = generate_temporary_password()
                            hashed_password = hash_password(temp_password)
                            
                            new_user = Users(
                                user_no=user_no,
                                full_name=mapped_record.get('full_name', ''),
                                first_name=mapped_record.get('first_name', ''),
                                last_name=mapped_record.get('last_name', ''),
                                middle_name=mapped_record.get('middle_name', ''),
                                email=mapped_record.get('email', ''),
                                login_name=mapped_record.get('login_name'),
                                login_password=hashed_password,
                                require_password_change=True,
                                entered_by=mapped_record.get('entered_by', 0),
                                last_modified_by=mapped_record.get('last_modified_by', 0)
                            )
                            
                            if mapped_record.get('entered_at'):
                                new_user.entered_at = mapped_record.get('entered_at')
                            if mapped_record.get('last_modified_at'):
                                new_user.last_modified_at = mapped_record.get('last_modified_at')
                            
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            
                            self.stats['inserted'] += 1
                            logger.info(f"Created new User with user_no={user_no}, email={mapped_record.get('email')}")
                            
                            user_email = "devendra.la@cisinlabs.com"
                            if user_email:
                                full_name = mapped_record.get('full_name', '')
                                first_name = full_name.split()[0] if full_name else 'User'
                                login_name = mapped_record.get('login_name') or user_email
                                
                                email_sent = send_user_welcome_notification(
                                    email=user_email,
                                    first_name=first_name,
                                    login_name=login_name,
                                    temp_password=temp_password
                                )
                                
                                if email_sent:
                                    self.stats['emails_sent'] += 1
                                    logger.info(f"Welcome email sent to {user_email}")
                                else:
                                    logger.warning(f"Failed to send welcome email to {user_email}")
                            else:
                                logger.warning(f"No email address for User user_no={user_no}, skipping welcome email")
                    
                    except Exception as e:
                        logger.error(
                            f"Error processing User record with user_no={user_no}: {str(e)}",
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
                f"Stage 2 Users sync completed: "
                f"Inserted={self.stats['inserted']}, "
                f"Updated={self.stats['updated']}, "
                f"Errors={self.stats['errors']}, "
                f"Skipped={self.stats['skipped']}, "
                f"EmailsSent={self.stats['emails_sent']}"
            )
        
        except Exception as e:
            logger.error(f"Failed to sync Users in Stage 2: {str(e)}", exc_info=True)
            self.stats['errors'] += 1
            try:
                if 'db' in locals():
                    db.close()
            except Exception:
                pass
        
        return self.stats

