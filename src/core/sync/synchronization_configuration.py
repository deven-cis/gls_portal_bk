from typing import Dict, Any, List

# Dependency order for syncing tables (must sync in this order)
SYNC_ORDER = [
    'Users',
    'Cases',
    'Jobs'
]


# Table configurations for Stage 2 (rb9_db → new_gls_db)
STAGE2_TABLE_CONFIG = {
    'Users': {
        'table_name': 'Users',
        'rb9_table': 'Users',
        'unique_field': 'user_no',
        'rb9_unique_field': 'UserNo',
        'query': '''
            SELECT 
                "UserNo",
                "PersonNo",
                "FullName",
                "FirstName",
                "MiddleName",
                "LastName",
                "LoginName",
                "Email",
                "IsActive",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy",
                "CreatedAtRb",
                "UpdatedAtRb"
            FROM "Users"
        ''',
        'field_mapping': {
            'UserNo': 'user_no',
            'PersonNo': 'person_no',
            'FullName': 'full_name',
            'FirstName': 'first_name',
            'MiddleName': 'middle_name',
            'LastName': 'last_name',
            'LoginName': 'login_name',
            'Email': 'email',
            'IsActive': 'is_active',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by',
            'Entered': 'entered_at',
            'EnteredBy': 'entered_by'
        },
        'date_field': 'LastModified',
        'model_class': 'Users'
    },
    'Cases': {
        'table_name': 'Cases',
        'rb9_table': 'Cases',
        'unique_field': 'case_no',
        'rb9_unique_field': 'CaseNo',
        'query': '''
            SELECT 
                c."CaseNo",
                c."CaseShortName",
                c."CaseFullName",
                c."CauseNo",
                lt."ListValue" AS "CaseType",
                ls."ListValue" AS "Status",
                c."TrialDate",
                c."LastModified",
                c."LastModifiedBy",
                c."Entered",
                c."EnteredBy",
                c."CreatedAtRb",
                c."UpdatedAtRb"
            FROM "Cases" c
            LEFT JOIN "Lists" lt ON c."CaseType" = lt."ListNo"
            LEFT JOIN "Lists" ls ON c."Status" = ls."ListNo"
        ''',
        'field_mapping': {
            'CaseNo': 'case_no',
            'CaseShortName': 'case_short_name',
            'CaseFullName': 'case_full_name',
            'CauseNo': 'case_number',
            'CaseType': 'case_type',
            'Status': 'status',
            'TrialDate': 'trial_date',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by',
            'Entered': 'entered_at',
            'EnteredBy': 'entered_by'
        },
        'date_field': 'LastModified',
        'date_field_table_alias': 'c',  
        'model_class': 'Cases'
    },
    'Jobs': {
        'table_name': 'Jobs',
        'rb9_table': 'Jobs',
        'unique_field': 'job_no',
        'rb9_unique_field': 'JobNo',
        'query': '''
            SELECT 
                j."JobNo",
                j."JobDate"::timestamp AS "JobDate",
                j."StartTime",
                j."EndTime",
                t."TimezoneName" AS "TimezoneName",
                j."CaseNo",
                ls."ListValue" AS "Status",
                lt."ListValue" AS "JobType",
                j."ScheduledByEmail",
                j."JobLocName",
                j."JobLocAddress",
                j."JobLocCity",
                j."JobLocState",
                j."JobLocZip",
                j."SchedulingNotesHtml",
                j."ZoomMeetingId",
                j."ConfirmationNotesHtml",
                j."LastModified",
                j."LastModifiedBy",
                j."Entered",
                j."EnteredBy",
                j."CreatedAtRb",
                j."UpdatedAtRb"
            FROM "Jobs" j
            LEFT JOIN "Timezones" t ON j."TimezoneNo" = t."TimezoneNo"
            LEFT JOIN "Lists" ls ON j."Status" = ls."ListNo"
            LEFT JOIN "Lists" lt ON j."JobType" = lt."ListNo"
            WHERE j."CaseNo" IS NOT NULL
        ''',
        'field_mapping': {
            'JobNo': 'job_no',
            'JobDate': 'job_date',
            'StartTime': 'start_time',
            'EndTime': 'end_time',
            'TimezoneName': 'timezone_name',
            'CaseNo': 'case_no',
            'Status': 'status',
            'JobType': 'job_type',
            'ScheduledByEmail': 'scheduled_by_email',
            'JobLocName': 'job_loc_name',
            'JobLocAddress': 'job_loc_address',
            'JobLocCity': 'job_loc_city',
            'JobLocState': 'job_loc_state',
            'JobLocZip': 'job_loc_zip',
            'SchedulingNotesHtml': 'scheduling_notes_html',
            'ZoomMeetingId': 'zoom_meeting_id',
            'ConfirmationNotesHtml': 'confirmation_notes_html',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by',
            'Entered': 'entered_at',
            'EnteredBy': 'entered_by',
        },
        'date_field': 'LastModified',
        'date_field_table_alias': 'j',
        'model_class': 'Jobs'
    }
}


def get_table_config_stage2(table_name: str) -> Dict[str, Any]:
    return STAGE2_TABLE_CONFIG.get(table_name, {})


def get_sync_order() -> List[str]:
    return SYNC_ORDER.copy()

