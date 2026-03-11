from typing import Dict, Any, List

# Dependency order for syncing tables (must sync in this order)
SYNC_ORDER = [
    'Resources',
    'Cases',
    'Jobs',
    'JobsTasks'
]


# Table configurations for Stage 2 (rb9_db → new_gls_db)
STAGE2_TABLE_CONFIG = {
    'Resources': {
    'table_name': 'Resources',
    'rb9_table': 'Resources',
    'unique_field': 'rsrc_no',
    'rb9_unique_field': 'RsrcNo',
    'query': '''
        SELECT 
            r."RsrcNo",
            r."PersonNo",
            r."FullName",
            r."FirstName",
            r."MiddleName",
            r."LastName",
            r."MainPhone",
            r."AltPhone",
            r."Fax",
            r."Mobile",
            r."SMSProviderNo",
            r."LoginName",
            r."Email",
            r."IsActive",
            r."IsLocked",
            r."TryLoginCnt",
            r."LastPwdChanged",
            r."SessionId",
            r."Address",
            r."City",
            r."State",
            r."Zip",
            r."Country",
            r."Directions",
            r."Warning",
            r."StartDate",
            r."EndDate",
            r."IsNoPay",
            r."CommissionRateCover",
            r."CommissionRateNoCover",
            r."IsSelfScope",
            r."RecurringAmt",
            r."RecurringFrom",
            r."RecurringTo",
            r."IsDirectDeposit",
            r."WorkScheduleSun",
            r."WorkScheduleMon",
            r."WorkScheduleTue",
            r."WorkScheduleWed",
            r."WorkScheduleThu",
            r."WorkScheduleFri",
            r."WorkScheduleSat",
            r."LastModified",
            r."LastModifiedBy",
            r."Entered",
            r."EnteredBy",
            r."CreateAtRb",
            r."UpdateAtRb",
            l_salutation."ListValue"  AS "Salutation",
            l_rsrc_type."ListValue"   AS "RsrcType",
            l_priority."ListValue"    AS "PriorityLevel",
            l_pay_rate."ListValue"    AS "PayRateGroup",
            l_pay_group."ListValue"   AS "PayGroup"
        FROM "Resources" r
        LEFT JOIN "Lists" l_salutation  ON r."Salutaion"     = l_salutation."ListNo"
        LEFT JOIN "Lists" l_rsrc_type   ON r."RsrcType"      = l_rsrc_type."ListNo"
        LEFT JOIN "Lists" l_priority    ON r."PriorityLevel" = l_priority."ListNo"
        LEFT JOIN "Lists" l_pay_rate    ON r."PayRateGroup"  = l_pay_rate."ListNo"
        LEFT JOIN "Lists" l_pay_group   ON r."PayGroup"      = l_pay_group."ListNo"
    ''',
    'field_mapping': {
        'RsrcNo':               'rsrc_no',
        'PersonNo':             'person_no',
        'FullName':             'full_name',
        'FirstName':            'first_name',
        'MiddleName':           'middle_name',
        'LastName':             'last_name',
        'MainPhone':            'main_phone',
        'AltPhone':             'alt_phone',
        'Fax':                  'fax',
        'Mobile':               'mobile',
        'SMSProviderNo':        'sms_provider_no',
        'LoginName':            'login_name',
        'Email':                'email',
        'IsActive':             'is_active',
        'IsLocked':             'is_locked',
        'TryLoginCnt':          'try_login_cnt',
        'LastPwdChanged':       'last_pwd_changed',
        'SessionId':            'session_id',
        'Salutation':           'salutation',
        'RsrcType':             'rsrc_type',
        'PriorityLevel':        'priority_level',
        'PayRateGroup':         'pay_rate_group',
        'PayGroup':             'pay_group',
        'Address':              'address',
        'City':                 'city',
        'State':                'state',
        'Zip':                  'zip',
        'Country':              'country',
        'Directions':           'directions',
        'Warning':              'warning',
        'StartDate':            'start_date',
        'EndDate':              'end_date',
        'IsNoPay':              'is_no_pay',
        'CommissionRateCover':  'commission_rate_cover',
        'CommissionRateNoCover':'commission_rate_no_cover',
        'IsSelfScope':          'is_self_scope',
        'RecurringAmt':         'recurring_amt',
        'RecurringFrom':        'recurring_from',
        'RecurringTo':          'recurring_to',
        'IsDirectDeposit':      'is_direct_deposit',
        'WorkScheduleSun':      'work_schedule_sun',
        'WorkScheduleMon':      'work_schedule_mon',
        'WorkScheduleTue':      'work_schedule_tue',
        'WorkScheduleWed':      'work_schedule_wed',
        'WorkScheduleThu':      'work_schedule_thu',
        'WorkScheduleFri':      'work_schedule_fri',
        'WorkScheduleSat':      'work_schedule_sat',
        'LastModified':         'last_modified_at',
        'LastModifiedBy':       'last_modified_by',
        'Entered':              'entered_at',
        'EnteredBy':            'entered_by',
    },
    'date_field': 'LastModified',
    'model_class': 'Resources'

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
                c."CreateAtRb",
                c."UpdateAtRb"
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
                j."CreateAtRb",
                j."UpdateAtRb"
            FROM "Jobs" j
            LEFT JOIN "Timezones" t ON j."TimezoneNo" = t."TimezoneNo"
            LEFT JOIN "Lists" ls ON j."Status" = ls."ListNo"
            LEFT JOIN "Lists" lt ON j."JobType" = lt."ListNo"
            WHERE j."CaseNo" IS NOT NULL
            AND ls."ListValue" IN (
                'Back order',
                'Confirmed',
                'New',
                'Will Call Back',
                'Request New',
                'Request Confirm'
            )
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
    },
    'JobsTasks': {
        'table_name': 'JobsTasks',
        'rb9_table': 'JobsTasks',
        'unique_field': 'task_no',
        'rb9_unique_field': 'TaskNo',
        'query': '''
            SELECT 
                jt."TaskNo",
                jt."JobNo",
                jt."RsrcNo",
                jt."TaskListNote",
                jt."NotifiedDate",
                jt."OrderDate",
                jt."DueDate",
                jt."CancelDate",
                jt."AcknowledgedDate",
                jt."EstimatedDeliveryDate",
                jt."TurnInDate",
                jt."CancelBy",
                jt."EstimatedPages",
                jt."TaskNotes",
                jt."RsrcNotes",
                jt."LastModified",
                jt."LastModifiedBy",
                jt."Entered",
                jt."EnteredBy",
                jt."CreateAtRb",
                jt."UpdateAtRb"
            FROM "JobsTasks" jt
            LEFT JOIN "Jobs" j ON jt."JobNo" = j."JobNo"
            LEFT JOIN "Resources" r ON jt."RsrcNo" = r."RsrcNo"
            WHERE jt."JobNo" IS NOT NULL
        ''',
        'field_mapping': {
            'TaskNo': 'task_no',
            'JobNo': 'job_no',
            'RsrcNo': 'rsrc_no',
            'TaskListNote': 'task_list_note',
            'NotifiedDate': 'notified_date',
            'OrderDate': 'order_date',
            'DueDate': 'due_date',
            'CancelDate': 'cancel_date',
            'AcknowledgedDate': 'acknowledged_date',
            'EstimatedDeliveryDate': 'estimated_delivery_date',
            'TurnInDate': 'turn_in_date',
            'CancelBy': 'cancel_by',
            'EstimatedPages': 'estimated_pages',
            'TaskNotes': 'task_notes',
            'RsrcNotes': 'rsrc_notes',
            'LastModified': 'last_modified_at',
            'LastModifiedBy': 'last_modified_by',
            'Entered': 'entered_at',
            'EnteredBy': 'entered_by'
        },
        'date_field': 'LastModified',
        'date_field_table_alias': 'jt',
        'model_class': 'JobsTasks'
    },
}


def get_table_config_stage2(table_name: str) -> Dict[str, Any]:
    return STAGE2_TABLE_CONFIG.get(table_name, {})


def get_sync_order() -> List[str]:
    return SYNC_ORDER.copy()

