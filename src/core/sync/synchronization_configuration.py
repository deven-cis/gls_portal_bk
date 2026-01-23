from typing import Dict, Any, List

# Dependency order for syncing tables (must sync in this order)
SYNC_ORDER = [
    'Users',
    'Lists',
    'Cases',
    'Timezones',
    'Jobs'
]

# Table configurations for Stage 1 (External DB → rb9_db)
STAGE1_TABLE_CONFIG = {
    'Users': {
        'table_name': 'Users',
        'unique_field': 'UserNo',
        'query': '''
            SELECT 
                "UserNo",
                "FullName",
                "FirstName",
                "MiddleName",
                "LastName",
                "LoginName",
                "LoginPassword",
                "Email",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy"
            FROM "Users"
        ''',
        'date_field': 'LastModified',
        'exclude_fields': ['CreateAtRb', 'UpdateAtRb']
    },
    'Lists': {
        'table_name': 'Lists',
        'unique_field': 'ListNo',
        'query': '''
            SELECT 
                "ListNo",
                "ListValue",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy"
            FROM "Lists"
        ''',
        'date_field': 'LastModified',
        'exclude_fields': ['CreateAtRb', 'UpdateAtRb']
    },
    'Cases': {
        'table_name': 'Cases',
        'unique_field': 'CaseNo',
        'query': '''
            SELECT 
                "CaseNo",
                "CaseShortName",
                "CaseFullName",
                "CaseType",
                "Status",
                "TrialDate",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy"
            FROM "Cases"
        ''',
        'date_field': 'LastModified',
        'exclude_fields': ['CreateAtRb', 'UpdateAtRb']
    },
    'Timezones': {
        'table_name': 'Timezones',
        'unique_field': 'TimezoneNo',
        'query': '''
            SELECT 
                "TimezoneNo",
                "TimezoneName",
                "TimezoneFullName",
                "StandardBias",
                "DaylightBias",
                "IsActive",
                "LastModified",
                "LastModifiedBy"
            FROM "Timezones"
        ''',
        'date_field': 'LastModified',
        'exclude_fields': ['CreateAtRb', 'UpdateAtRb']
    },
    'Jobs': {
        'table_name': 'Jobs',
        'unique_field': 'JobNo',
        'query': '''
            SELECT 
                "JobNo",
                "JobDate",
                "StartTime",
                "EndTime",
                "TimezoneNo",
                "CaseNo",
                "JobType",
                "ScheduledByEmail",
                "JobLocName",
                "JobLocAddress",
                "JobLocCity",
                "JobLocState",
                "JobLocZip",
                "SchedulingNotesHtml",
                "ZoomMeetingId",
                "ConfirmationNotesHtml",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy"
            FROM "Jobs"
        ''',
        'date_field': 'LastModified',
        'exclude_fields': ['CreateAtRb', 'UpdateAtRb']
    }
}

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
                "FullName",
                "FirstName",
                "MiddleName",
                "LastName",
                "LoginName",
                "LoginPassword",
                "Email",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy"
            FROM "Users"
        ''',
        'field_mapping': {
            'UserNo': 'user_no',
            'FullName': 'full_name',
            'FirstName': 'first_name',
            'MiddleName': 'middle_name',
            'LastName': 'last_name',
            'LoginName': 'login_name',
            'LoginPassword': 'login_password',
            'Email': 'email',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by',
            'Entered': 'entered_at',
            'EnteredBy': 'entered_by'
        },
        'date_field': 'LastModified',
        'model_class': 'Users'
    },
    'Lists': {
        'table_name': 'Lists',
        'rb9_table': 'Lists',
        'unique_field': 'list_no',
        'rb9_unique_field': 'ListNo',
        'query': '''
            SELECT 
                "ListNo",
                "ListValue",
                "LastModified",
                "LastModifiedBy",
                "Entered",
                "EnteredBy"
            FROM "Lists"
        ''',
        'field_mapping': {
            'ListNo': 'list_no',
            'ListValue': 'list_value',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by',
            'Entered': 'entered_at',
            'EnteredBy': 'entered_by'
        },
        'date_field': 'LastModified',
        'model_class': None
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
                lt."ListValue" AS "CaseType",
                ls."ListValue" AS "Status",
                c."TrialDate",
                c."LastModified",
                c."LastModifiedBy",
                c."Entered",
                c."EnteredBy"
            FROM "Cases" c
            LEFT JOIN "Lists" lt ON c."CaseType" = lt."ListNo"
            LEFT JOIN "Lists" ls ON c."Status" = ls."ListNo"
        ''',
        'field_mapping': {
            'CaseNo': 'case_no',
            'CaseShortName': 'case_short_name',
            'CaseFullName': 'case_full_name',
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
    'Timezones': {
        'table_name': 'Timezones',
        'rb9_table': 'Timezones',
        'unique_field': 'timezone_no',
        'rb9_unique_field': 'TimezoneNo',
        'query': '''
            SELECT 
                "TimezoneNo",
                "TimezoneName",
                "TimezoneFullName",
                "StandardBias",
                "DaylightBias",
                "IsActive",
                "LastModified",
                "LastModifiedBy"
            FROM "Timezones"
        ''',
        'field_mapping': {
            'TimezoneNo': 'timezone_no',
            'TimezoneName': 'timezone_name',
            'TimezoneFullName': 'timezone_full_name',
            'StandardBias': 'standard_bias',
            'DaylightBias': 'daylight_bias',
            'IsActive': 'is_active',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by'
        },
        'date_field': 'LastModified',
        'model_class': None
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
                j."JobType",
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
                j."EnteredBy"
            FROM "Jobs" j
            LEFT JOIN "Timezones" t ON j."TimezoneNo" = t."TimezoneNo"
            WHERE j."CaseNo" IS NOT NULL
        ''',
        'field_mapping': {
            'JobNo': 'job_no',
            'JobDate': 'job_date',
            'StartTime': 'start_time',
            'EndTime': 'end_time',
            'TimezoneName': 'timezone_name',
            'CaseNo': 'case_no',
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
            'EnteredBy': 'entered_by'
        },
        'date_field': 'LastModified',
        'date_field_table_alias': 'j',
        'model_class': 'Jobs'
    }
}


def get_table_config_stage1(table_name: str) -> Dict[str, Any]:
    return STAGE1_TABLE_CONFIG.get(table_name, {})


def get_table_config_stage2(table_name: str) -> Dict[str, Any]:
    return STAGE2_TABLE_CONFIG.get(table_name, {})


def get_sync_order() -> List[str]:
    return SYNC_ORDER.copy()

