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
    """
    Service for synchronizing Users from rb9_db to new_gls_db.
    Handles user onboarding including password generation, welcome email notifications,
    and field mapping (PascalCase → snake_case).
    """
    
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
        """
        Transform field names from PascalCase (rb9_db) to snake_case (new_gls_db).
        
        Args:
            rb9_record: Record from rb9_db with PascalCase fields
            field_mapping: Dictionary mapping PascalCase → snake_case
        
        Returns:
            Dictionary with snake_case fields
        """
        mapped_record = {}
        for rb9_field, new_gls_field in field_mapping.items():
            if rb9_field in rb9_record:
                mapped_record[new_gls_field] = rb9_record[rb9_field]
        return mapped_record
    
    def _find_existing_user(self, db: Session, user_no: int) -> Optional[Users]:
        """
        Find an existing user in new_gls_db by user_no.
        
        Args:
            db: Database session
            user_no: User number to search for
        
        Returns:
            Users object if exists, None otherwise
        """
        return db.query(Users).filter(Users.user_no == user_no).first()
    
    def _detect_field_changes(
        self,
        existing_user: Users,
        mapped_record: Dict[str, Any],
        exclude_fields: list = None
    ) -> Dict[str, Any]:
        """
        Detect which fields have changed between existing user and new data.
        
        Args:
            existing_user: Existing Users object
            mapped_record: New data with snake_case fields
            exclude_fields: Fields to exclude from comparison
        
        Returns:
            Dictionary of changed fields with their new values
        """
        exclude_fields = exclude_fields or []
        exclude_fields.extend(['id', 'entered_at', 'entered_by', 'last_modified_at', 'last_modified_by', 'is_archived', 'login_password'])
        
        changes = {}
        for field, new_value in mapped_record.items():
            if field in exclude_fields:
                continue
            
            existing_value = getattr(existing_user, field, None)
            
            # Compare values (handle None cases)
            if existing_value != new_value:
                # Check if both are None
                if existing_value is None and new_value is None:
                    continue
                # Check if one is None
                if existing_value is None or new_value is None:
                    changes[field] = new_value
                else:
                    # Both have values, compare
                    if str(existing_value) != str(new_value):
                        changes[field] = new_value
        
        return changes
    
    def synchronize_users(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Synchronize Users from rb9_db to new_gls_db.
        Handles password generation and welcome email for new users.
        
        Args:
            start_date: Start date for LastModified filter (for testing, use static date)
            end_date: End date for LastModified filter
            limit: Limit number of records (for testing)
        
        Returns:
            Dictionary with synchronization statistics
        """
        self.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0, 'emails_sent': 0}
        
        # Get table configuration
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
            
            logger.info(f"Fetching Users from rb9_db...")
            logger.debug(f"Query: {query[:200]}...")
            
            # Fetch records from rb9_db
            rb9_records = self.rb9_db.execute_query(query, params)
            logger.info(f"Fetched {len(rb9_records)} Users from rb9_db")
            
            if not rb9_records:
                logger.info("No Users to sync")
                return self.stats
            
            # Process each record
            db: Session = SessionLocal()
            try:
                for rb9_record in rb9_records:
                    try:
                        user_no = rb9_record.get(unique_field)
                        if not user_no:
                            logger.warning(f"Skipping User record - missing {unique_field}")
                            self.stats['skipped'] += 1
                            continue
                        
                        # Transform field names from PascalCase to snake_case
                        mapped_record = self._transform_field_names(rb9_record, field_mapping)
                        
                        # Find existing user
                        existing_user = self._find_existing_user(db, user_no)
                        
                        if existing_user:
                            # Detect field changes
                            changes = self._detect_field_changes(existing_user, mapped_record)
                            
                            if changes:
                                # Update fields (only if they exist in the model)
                                # Exclude login_password from updates (it's binary and should only be set on creation)
                                for field, value in changes.items():
                                    if field == 'login_password':
                                        continue  # Skip password updates - passwords should only be set on user creation
                                    if hasattr(existing_user, field):
                                        setattr(existing_user, field, value)
                                
                                # Update tracking fields (if they exist)
                                # Note: create_at_rb and update_at_rb may need to be added via migration
                                # For now, we'll update last_modified_at
                                existing_user.last_modified_at = datetime.utcnow()
                                
                                db.commit()
                                db.refresh(existing_user)
                                
                                self.stats['updated'] += 1
                                logger.debug(f"Updated User with user_no={user_no}")
                            else:
                                self.stats['skipped'] += 1
                                logger.debug(f"No changes for User with user_no={user_no}, skipping")
                        else:
                            # Create new user
                            # Generate temporary password for new users
                            temp_password = generate_temporary_password()
                            hashed_password = hash_password(temp_password)
                            
                            # Create new user object (only use fields that exist in Users model)
                            new_user = Users(
                                user_no=user_no,
                                full_name=mapped_record.get('full_name', ''),
                                email=mapped_record.get('email', ''),
                                login_name=mapped_record.get('login_name'),
                                login_password=hashed_password,
                                require_password_change=True,
                                entered_by=mapped_record.get('entered_by', 0),
                                last_modified_by=mapped_record.get('last_modified_by', 0)
                            )
                            
                            # Set timestamp fields if provided
                            if mapped_record.get('entered_at'):
                                new_user.entered_at = mapped_record.get('entered_at')
                            if mapped_record.get('last_modified_at'):
                                new_user.last_modified_at = mapped_record.get('last_modified_at')
                            
                            db.add(new_user)
                            db.commit()
                            db.refresh(new_user)
                            
                            self.stats['inserted'] += 1
                            logger.info(f"Created new User with user_no={user_no}, email={mapped_record.get('email')}")
                            
                            # Send welcome email to new user
                            user_email = "devendra.la@cisinlabs.com"
                            if user_email:
                                # Extract first name from full_name or use full_name
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
                        logger.error(f"Error processing User record: {str(e)}", exc_info=True)
                        self.stats['errors'] += 1
                        db.rollback()
                        continue
                
            finally:
                db.close()
            
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
        
        return self.stats

