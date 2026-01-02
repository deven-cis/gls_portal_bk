--
-- PostgreSQL database dump
--

\restrict 3IPnf786KqN67iwDZYUJm5f9iK1osF7piq8CV15n4optAokiD2IUW7S2b0w011o

-- Dumped from database version 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 16.10 (Ubuntu 16.10-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: cancel_reason_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.cancel_reason_enum AS ENUM (
    'HEARING_RESCHEDULED',
    'WITNESS_ABSENT',
    'ATTORNEY_ABSENT',
    'JUDGE_ABSENT'
);


ALTER TYPE public.cancel_reason_enum OWNER TO postgres;

--
-- Name: job_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.job_status_enum AS ENUM (
    'UPCOMING',
    'SESSION_NOT_STARTED',
    'SESSION_IN_PROGRESS',
    'COMPLETED',
    'CANCELLED'
);


ALTER TYPE public.job_status_enum OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: additional_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.additional_documents (
    job_no integer NOT NULL,
    billing_id integer,
    equipment_time_id integer,
    file_name text,
    file_path text,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false
);


ALTER TABLE public.additional_documents OWNER TO postgres;

--
-- Name: additional_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.additional_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.additional_documents_id_seq OWNER TO postgres;

--
-- Name: additional_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.additional_documents_id_seq OWNED BY public.additional_documents.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: attorneys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attorneys (
    job_no integer NOT NULL,
    attorney_name character varying(255) NOT NULL,
    firm_name character varying(255) NOT NULL,
    notes text NOT NULL,
    order_details text NOT NULL,
    file_name text,
    file_name_path text,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false,
    mark_is_done boolean DEFAULT false
);


ALTER TABLE public.attorneys OWNER TO postgres;

--
-- Name: attorneys_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attorneys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attorneys_id_seq OWNER TO postgres;

--
-- Name: attorneys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attorneys_id_seq OWNED BY public.attorneys.id;


--
-- Name: billings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.billings (
    job_no integer NOT NULL,
    cancel_en_route boolean,
    cancel_setup boolean,
    billing_notes text,
    videographer_hours_present character varying(255),
    file_hours_length character varying(255),
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false,
    mark_is_done boolean DEFAULT false
);


ALTER TABLE public.billings OWNER TO postgres;

--
-- Name: billings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.billings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.billings_id_seq OWNER TO postgres;

--
-- Name: billings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.billings_id_seq OWNED BY public.billings.id;


--
-- Name: cases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cases (
    case_short_name character varying,
    case_full_name character varying,
    case_type character varying,
    status character varying,
    trial_date timestamp without time zone,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    case_no integer,
    is_archived boolean DEFAULT false,
    case_number integer,
    mark_is_done boolean DEFAULT false,
    progress_percentage double precision,
    total_jobs integer,
    completed_jobs integer,
    case_status character varying(50)
);


ALTER TABLE public.cases OWNER TO postgres;

--
-- Name: cases_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.cases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cases_id_seq OWNER TO postgres;

--
-- Name: cases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.cases_id_seq OWNED BY public.cases.id;


--
-- Name: equipment_time; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.equipment_time (
    job_no integer NOT NULL,
    laptop_used boolean,
    pip_used boolean,
    exhibit_tech boolean,
    parking_cost numeric(10,2) DEFAULT 0.00,
    time_after time without time zone,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false,
    mark_is_done boolean DEFAULT false
);


ALTER TABLE public.equipment_time OWNER TO postgres;

--
-- Name: equipment_time_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.equipment_time_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_time_id_seq OWNER TO postgres;

--
-- Name: equipment_time_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.equipment_time_id_seq OWNED BY public.equipment_time.id;


--
-- Name: job_assignments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.job_assignments (
    assigner_id integer NOT NULL,
    assignee_id integer NOT NULL,
    job_no integer NOT NULL,
    case_no integer,
    reason text,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false
);


ALTER TABLE public.job_assignments OWNER TO postgres;

--
-- Name: job_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.job_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.job_assignments_id_seq OWNER TO postgres;

--
-- Name: job_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.job_assignments_id_seq OWNED BY public.job_assignments.id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jobs (
    job_date timestamp without time zone NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    timezone_no integer,
    status character varying(255) NOT NULL,
    case_no integer NOT NULL,
    job_type character varying(255),
    scheduled_by_email character varying(255),
    job_loc_name character varying(255),
    job_loc_address character varying(255),
    job_loc_city character varying(255),
    job_loc_state character varying(255),
    job_loc_zip character varying(255),
    scheduling_notes_html character varying,
    zoom_meeting_id bigint,
    confirmation_notes_html character varying,
    cancel_by integer,
    cancel_date timestamp without time zone,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    job_no integer,
    cancel_details text,
    cancel_resone public.cancel_reason_enum,
    computed_status character varying(50),
    is_archived boolean DEFAULT false,
    actual_session_start_time timestamp without time zone,
    actual_session_end_time timestamp without time zone,
    session_duration character varying(8),
    session_completed boolean DEFAULT false,
    mark_is_done boolean DEFAULT false,
    video_upload_deadline timestamp without time zone,
    expected_video_count integer,
    mark_is_done_case boolean DEFAULT false,
    mark_is_done_witnesses boolean DEFAULT false,
    mark_is_done_attorneys boolean DEFAULT false,
    mark_is_done_billings boolean DEFAULT false,
    mark_is_done_equipment_time boolean DEFAULT false
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jobs_id_seq OWNER TO postgres;

--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.jobs_id_seq OWNED BY public.jobs.id;


--
-- Name: repositories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.repositories (
    wit_no integer NOT NULL,
    file_name character varying,
    repository_level character varying(255),
    file_path character varying,
    job_no integer NOT NULL,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false
);


ALTER TABLE public.repositories OWNER TO postgres;

--
-- Name: repositories_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.repositories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.repositories_id_seq OWNER TO postgres;

--
-- Name: repositories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.repositories_id_seq OWNED BY public.repositories.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    full_name character varying NOT NULL,
    email character varying NOT NULL,
    login_name character varying NOT NULL,
    login_password bytea,
    profile_image_url character varying,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    last_modified_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_by integer NOT NULL,
    require_password_change boolean,
    is_archived boolean DEFAULT false
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: witness_videos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.witness_videos (
    wit_no integer NOT NULL,
    job_no integer NOT NULL,
    start_time character varying(255),
    end_time character varying(255),
    file_name text,
    file_path text,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    is_archived boolean DEFAULT false
);


ALTER TABLE public.witness_videos OWNER TO postgres;

--
-- Name: witness_videos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.witness_videos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.witness_videos_id_seq OWNER TO postgres;

--
-- Name: witness_videos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.witness_videos_id_seq OWNED BY public.witness_videos.id;


--
-- Name: witnesses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.witnesses (
    witness_name character varying(255) NOT NULL,
    witness_email character varying(255),
    actual_start_time character varying(255),
    actual_end_time character varying(255),
    read_sign_date timestamp without time zone,
    read_sign_to integer,
    id integer NOT NULL,
    entered_at timestamp without time zone,
    entered_by integer NOT NULL,
    last_modified_at timestamp without time zone,
    last_modified_by integer NOT NULL,
    wit_no integer,
    job_no integer NOT NULL,
    read_on_text text DEFAULT ''::text NOT NULL,
    read_off_text text DEFAULT ''::text NOT NULL,
    read_on_time character varying(255),
    read_off_time character varying(255),
    is_archived boolean DEFAULT false,
    mark_is_done boolean DEFAULT false
);


ALTER TABLE public.witnesses OWNER TO postgres;

--
-- Name: witnesses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.witnesses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.witnesses_id_seq OWNER TO postgres;

--
-- Name: witnesses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.witnesses_id_seq OWNED BY public.witnesses.id;


--
-- Name: additional_documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.additional_documents ALTER COLUMN id SET DEFAULT nextval('public.additional_documents_id_seq'::regclass);


--
-- Name: attorneys id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attorneys ALTER COLUMN id SET DEFAULT nextval('public.attorneys_id_seq'::regclass);


--
-- Name: billings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.billings ALTER COLUMN id SET DEFAULT nextval('public.billings_id_seq'::regclass);


--
-- Name: cases id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases ALTER COLUMN id SET DEFAULT nextval('public.cases_id_seq'::regclass);


--
-- Name: equipment_time id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.equipment_time ALTER COLUMN id SET DEFAULT nextval('public.equipment_time_id_seq'::regclass);


--
-- Name: job_assignments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_assignments ALTER COLUMN id SET DEFAULT nextval('public.job_assignments_id_seq'::regclass);


--
-- Name: jobs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs ALTER COLUMN id SET DEFAULT nextval('public.jobs_id_seq'::regclass);


--
-- Name: repositories id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.repositories ALTER COLUMN id SET DEFAULT nextval('public.repositories_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: witness_videos id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witness_videos ALTER COLUMN id SET DEFAULT nextval('public.witness_videos_id_seq'::regclass);


--
-- Name: witnesses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witnesses ALTER COLUMN id SET DEFAULT nextval('public.witnesses_id_seq'::regclass);


--
-- Data for Name: additional_documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.additional_documents (job_no, billing_id, equipment_time_id, file_name, file_path, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived) FROM stdin;
3907	8	\N	Free_Test_Data_2.15MB_PDF.pdf	uploads/billings/a02c4282-090d-4c21-bbe4-8eee763647b8.pdf	17	2025-12-19 16:12:19.569497	1	2025-12-31 09:29:18.245383	1	t
3907	\N	11	file-sample_100kB.docx	uploads/equipment_time/31db274d-0f5b-417e-b4a9-9571bcfb6d95.docx	19	2025-12-19 16:13:10.773133	1	2025-12-31 09:29:18.245383	1	t
3086	3	\N	file-sample_1MB.docx	uploads/billings/a1eb9a70-639a-40a5-b3bf-b681b7a001b3.docx	5	2025-12-17 16:09:44.435484	1001	2025-12-17 16:09:44.435453	1001	f
3086	3	\N	Free_Test_Data_2.15MB_PDF.pdf	uploads/billings/96e9e76f-d8cc-4e97-999f-e16b67091038.pdf	6	2025-12-17 16:09:44.440697	1001	2025-12-17 16:09:44.440668	1001	f
3086	1	\N	file-sample_500kB.docx	uploads/billings/1047ecd1-bb1e-48c9-8f77-645fde076dd0.docx	7	2025-12-17 17:05:16.554205	1001	2025-12-17 17:05:16.554174	1001	f
3086	1	\N	file-sample_1MB.docx	uploads/billings/b7abf063-15d3-47e9-85c7-920925360b6b.docx	8	2025-12-17 17:05:42.288486	1001	2025-12-17 17:05:42.288445	1001	f
3086	5	\N	file-sample_1MB.docx	uploads/billings/5b8e7922-51b6-46a4-af1d-5b065ac8a85e.docx	9	2025-12-17 17:56:09.282127	1001	2025-12-17 17:56:09.282095	1001	f
3086	7	\N	file-sample_500kB.docx	uploads/billings/09710296-f881-4dbb-826b-279221a5ddde.docx	10	2025-12-17 18:44:45.107563	1001	2025-12-17 18:44:50.459684	1001	t
3086	7	\N	file-sample_1MB.docx	uploads/billings/a8400802-b7ae-4bd8-beda-00548cfc3cb9.docx	12	2025-12-17 18:45:08.383252	1001	2025-12-17 19:50:51.244141	1001	t
3086	7	\N	file-sample_500kB.docx	uploads/billings/af45f20e-86ec-43fd-8a13-2d0190a8e33f.docx	11	2025-12-17 18:45:08.373215	1001	2025-12-17 19:54:23.398687	1001	t
3086	\N	10	412KB.pdf	uploads/equipment_time/49bae56b-cf6e-48da-a116-126897fbccfe.pdf	14	2025-12-17 19:59:38.583883	1001	2025-12-17 20:00:14.556367	1001	t
3907	8	\N	412KB.pdf	uploads/billings/9222b915-9cf5-44f5-89b5-ac4a0cdb2aa7.pdf	16	2025-12-19 16:12:19.554782	1	2025-12-31 10:12:40.530729	1	f
3907	\N	11	file-sample_1MB.docx	uploads/equipment_time/8d0b606c-1b67-45f9-b3d7-1d1efdb49b9d.docx	18	2025-12-19 16:13:10.761919	1	2025-12-31 10:12:40.530729	1	f
3907	9	\N	file-sample_1MB.docx	uploads/billings/d0cc93d6-63a4-41d1-8ad2-427054275002.docx	20	2025-12-19 17:43:50.485716	1	2025-12-31 10:12:40.530729	1	f
3907	\N	13	Free_Test_Data_500KB_PDF.pdf	uploads/equipment_time/b76b5278-394c-4101-98c9-d55e2c8f43a8.pdf	23	2025-12-19 17:45:22.002625	1	2025-12-31 10:12:40.530729	1	f
3907	10	\N	file-sample_100kB.docx	uploads/billings/9f2c315d-3753-4248-a123-1d76d1c33038.docx	24	2025-12-19 19:32:24.876483	1	2025-12-31 10:12:40.530729	1	f
3295	12	\N	file-sample_500kB.docx	uploads/billings/f32accaa-98c6-43d1-ae82-eec7e2d7751b.docx	30	2025-12-22 20:38:22.888003	1001	2025-12-22 20:38:22.887973	1001	f
3295	\N	16	file-sample_500kB.docx	uploads/equipment_time/79375692-4151-40a3-8bed-c0a4016ef4af.docx	31	2025-12-22 20:38:56.890074	1001	2025-12-22 20:38:56.890053	1001	f
3106	13	\N	Free_Test_Data_500KB_PDF.pdf	uploads/billings/5be527b4-fe61-42e5-8694-3abfbe862f69.pdf	32	2025-12-23 16:59:03.670396	1001	2025-12-23 16:59:03.670355	1001	f
3106	\N	17	412KB.pdf	uploads/equipment_time/7ac89af2-df0b-4ecd-8f7e-3297695d32ab.pdf	33	2025-12-23 16:59:22.992644	1001	2025-12-23 16:59:22.992611	1001	f
3086	7	\N	412KB.pdf	uploads/billings/f1f1465b-c9bc-4a0e-a1ad-0001a01c5d4c.pdf	13	2025-12-17 19:54:23.410321	1001	2025-12-29 17:53:06.562423	1001	t
3086	7	\N	file-sample_500kB.docx	uploads/billings/bb845dd7-0d24-4208-95c6-17824923a8e9.docx	34	2025-12-29 17:53:06.573487	1001	2025-12-29 17:53:06.573457	1001	f
3086	\N	10	file-sample_500kB.docx	uploads/equipment_time/97b502bd-dc47-4187-98e4-a5ce7c5849f4.docx	15	2025-12-17 20:03:09.979489	1001	2025-12-29 18:06:23.96812	1001	t
3907	9	\N	file-sample_1MB.docx	uploads/billings/cc280d46-6f21-45ed-a716-d2d98f4e0eaf.docx	21	2025-12-19 17:43:50.500262	1	2025-12-31 09:29:18.245383	1	t
3907	\N	12	file-sample_1MB.docx	uploads/equipment_time/78cb7e3d-9145-480e-b05a-c6c31e14b6f6.docx	22	2025-12-19 17:44:39.188669	1	2025-12-31 09:29:18.245383	1	t
3907	\N	14	Free_Test_Data_2.15MB_PDF.pdf	uploads/equipment_time/546484b6-ca80-4876-98c8-4b1f948b84f4.pdf	25	2025-12-19 19:33:08.246316	1	2025-12-31 09:29:18.245383	1	t
3907	11	\N	file-sample_1MB.docx	uploads/billings/1de733e3-6d9f-4b76-bd54-036eb99d4bb2.docx	26	2025-12-19 20:14:01.843488	1	2025-12-31 09:29:18.245383	1	t
3907	11	\N	file-sample_100kB.docx	uploads/billings/b74b6900-a35f-4dca-8fba-356c4df251de.docx	27	2025-12-19 20:14:01.87008	1	2025-12-31 09:29:18.245383	1	t
3907	\N	15	file-sample_1MB.docx	uploads/equipment_time/200544d2-0beb-4be0-80b2-c6d7b1575403.docx	28	2025-12-19 20:18:15.122365	1	2025-12-31 10:12:40.530729	1	f
3907	14	\N	file-sample_1MB.docx	uploads/billings/b642bae9-4480-4f3e-b46f-4337c6499795.docx	35	2025-12-29 19:16:05.913654	1	2025-12-31 10:12:40.530729	1	f
3907	14	\N	Free_Test_Data_500KB_PDF.pdf	uploads/billings/4df2478f-383f-4747-bb2f-b31e71074d30.pdf	37	2025-12-29 19:16:05.935536	1	2025-12-31 10:12:40.530729	1	f
3907	\N	18	412KB.pdf	uploads/equipment_time/cef50036-a23f-42e6-8140-fc887459a4d3.pdf	38	2025-12-29 19:17:34.265492	1	2025-12-31 10:12:40.530729	1	f
3907	\N	18	file-sample_500kB.docx	uploads/equipment_time/2c1a8d03-4e11-4525-bb54-5d40c50dd03e.docx	40	2025-12-29 19:17:34.280486	1	2025-12-31 10:12:40.530729	1	f
3907	\N	15	file-sample_1MB.docx	uploads/equipment_time/53d8a21e-95e0-4bf7-93d5-96a9ebd1d31e.docx	29	2025-12-19 20:18:15.14773	1	2025-12-31 09:29:18.245383	1	t
3907	14	\N	Free_Test_Data_2.15MB_PDF.pdf	uploads/billings/e5fe2401-8885-4c05-b4eb-60ecb5c06650.pdf	36	2025-12-29 19:16:05.92758	1	2025-12-31 09:29:18.245383	1	t
3907	\N	18	file-sample_100kB.docx	uploads/equipment_time/4da5f938-9059-42e1-b74c-1761fe98d3ea.docx	39	2025-12-29 19:17:34.273674	1	2025-12-31 09:29:18.245383	1	t
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
8c8b2543a31f
\.


--
-- Data for Name: attorneys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attorneys (job_no, attorney_name, firm_name, notes, order_details, file_name, file_name_path, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived, mark_is_done) FROM stdin;
4100	shubham	admin	string	string	string	string	1	2025-12-05 18:01:06.232951	1001	2025-12-05 19:09:27.927312	1001	t	f
3106	Admin test	Jems	Working fine	nothing 	Packt.FastAPI.Cookbook (1).pdf	uploads/attorneys/38456a13-4783-4e64-af6b-03345588ab09.pdf	3	2025-12-16 17:57:13.700185	1001	2025-12-16 17:57:13.700115	1001	f	f
4100	devendra	lanjewar	nothing 	wr	AdminTest2.pdf	uploads/attorneys/a26c7f20-6878-4e9c-a9ef-25e8e4763d47.pdf	2	2025-12-05 19:02:21.557017	1001	2025-12-16 18:10:45.391063	1001	t	f
3086	sahil	ovels	Nothing	Do nothing	\N	\N	5	2025-12-16 20:33:05.654075	1001	2025-12-17 13:30:01.337583	1001	t	f
3086	shubham2	dsds	sd	fdf	\N	\N	9	2025-12-16 20:48:16.971915	1001	2025-12-17 13:43:49.046386	1001	t	f
3086	martin 	ovels 	Nothing 	add things	\N	\N	6	2025-12-16 20:34:30.376331	1001	2025-12-17 13:44:06.259926	1001	t	f
3086	shubham	lanj	ewe	ewe	Packt.FastAPI.Cookbook (1).pdf	uploads/attorneys/b8ce0ce0-b6ea-4090-b900-bfb935d8ecb2.pdf	8	2025-12-16 20:47:41.050629	1001	2025-12-17 13:44:08.872829	1001	t	f
3086	martin 	ovels 	Nothing 	add things	Packt.FastAPI.Cookbook (1).pdf	uploads/attorneys/1706289b-35b8-46bf-9da1-892be6c5724d.pdf	7	2025-12-16 20:35:53.989444	1001	2025-12-17 13:44:11.260276	1001	t	f
3086	martin	jose	we are working on that	the	\N	\N	4	2025-12-16 20:13:09.979719	1001	2025-12-17 13:44:13.250856	1001	t	f
3907	shubham	sds	dsd	sd	\N	\N	20	2025-12-19 19:28:53.873418	1	2025-12-31 09:29:18.227189	1	t	f
3086	Tom	James	Testing	test	file-sample_500kB.docx	uploads/attorneys/1e952720-7473-4105-aedb-421c179f3f35.docx	10	2025-12-17 13:47:38.464567	1001	2025-12-17 17:46:59.140603	1001	t	f
3086	sfsdf	dsfsd	sdfds	sdfsd	\N	\N	11	2025-12-17 18:02:00.224455	1001	2025-12-17 18:02:42.742801	1001	t	f
3086	ewqewq	ewqe	ewqe	weqe	file-sample_500kB.docx	uploads/attorneys/9061d162-f787-491d-9997-751db7533039.docx	12	2025-12-17 18:49:24.120537	1001	2025-12-17 20:01:38.562464	1001	t	f
3295	sajal 	Vishal	nothing 	fdfdf	file-sample_1MB.docx	uploads/attorneys/2a80a90c-9a4c-4bd8-b646-c99f61eb1aec.docx	33	2025-12-22 20:37:57.029633	1001	2025-12-22 20:37:57.029592	1001	f	f
3106	Sahil 	test	dsdsd	dsds	file-sample_1MB.docx	uploads/attorneys/abee0488-df51-46a5-8af5-e811e2acde38.docx	34	2025-12-23 16:58:40.301839	1001	2025-12-23 16:58:40.301805	1001	f	f
3086	jose	re	er	testtt	file-sample_500kB.docx	uploads/attorneys/d8e1b1c8-e58a-49c0-816f-c6a64bbbefbe.docx	13	2025-12-17 20:54:44.693256	1001	2025-12-29 17:42:09.665328	1001	t	f
3086	sdsd	dsds	sdsd	dsd	\N	\N	36	2025-12-29 17:42:42.50969	1001	2025-12-29 17:42:42.509663	1001	f	f
3086	sdsd	dsds	sdsd	dsd	\N	\N	37	2025-12-29 17:42:42.535904	1001	2025-12-29 17:42:42.535876	1001	f	f
3907	shubham	sds	dsd	sd	\N	\N	21	2025-12-19 19:29:40.826753	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsds	sds	dsd	sd	\N	\N	19	2025-12-19 19:28:39.505883	1	2025-12-31 09:29:18.227189	1	t	f
3907	shubham	sds	dsd	sd	\N	\N	22	2025-12-19 19:29:56.331618	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsfsf	sfs	sf	sf	\N	\N	18	2025-12-19 19:28:05.433324	1	2025-12-31 09:29:18.227189	1	t	f
3907	dfgdg	fdg	fdgdfdgfdg	dfgf	\N	\N	47	2025-12-29 19:05:00.384963	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsad	dsad	dsad	dsad	\N	\N	42	2025-12-29 18:42:51.778984	1	2025-12-31 09:29:18.227189	1	t	f
3907	fsere	ewr	ewr	rewr	\N	\N	23	2025-12-19 19:30:57.783885	1	2025-12-31 09:29:18.227189	1	t	f
3907	test	dsdsd	dsd	terer	412KB.pdf	uploads/attorneys/032444e2-1707-45ab-b54b-6c39a3fcfb08.pdf	14	2025-12-19 16:10:51.92037	1	2025-12-31 09:29:18.227189	1	t	f
3907	tesst	test	fddg	gfdg	\N	\N	15	2025-12-19 17:40:00.44559	1	2025-12-31 09:29:18.227189	1	t	f
3907	gry	emma	noth	etc	\N	\N	16	2025-12-19 17:42:17.739124	1	2025-12-31 09:29:18.227189	1	t	f
3907	gry	emma	noth	ewe	file-sample_500kB.docx	uploads/attorneys/89d186ff-43b1-4761-8665-21313b3c81ac.docx	17	2025-12-19 17:42:45.59766	1	2025-12-31 09:29:18.227189	1	t	f
3907	rewr	rewr	rewr	ewr	\N	\N	24	2025-12-19 19:34:44.609474	1	2025-12-31 09:29:18.227189	1	t	f
3907	shubham	s	s	dd	\N	\N	26	2025-12-19 19:42:11.904876	1	2025-12-31 09:29:18.227189	1	t	f
3907	shubham	s	s	dd	file-sample_1MB.docx	uploads/attorneys/15908943-067c-494d-87b5-0cf9a6f3e9a8.docx	25	2025-12-19 19:42:00.502961	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsd	sd	sdd	eer	\N	\N	30	2025-12-19 19:43:49.849047	1	2025-12-31 09:29:18.227189	1	t	f
3907	sds	dsd	sd	ds	\N	\N	29	2025-12-19 19:43:26.720924	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsd	sd	sdd	sd	file-sample_1MB.docx	uploads/attorneys/0fa7b6a2-37fe-4480-8b0f-b6ddf24e7f90.docx	28	2025-12-19 19:43:09.853083	1	2025-12-31 09:29:18.227189	1	t	f
3907	sds	dsd	sd	ds	file-sample_1MB.docx	uploads/attorneys/27c3308e-79b6-46e2-bbf6-d6dc35f8d35b.docx	27	2025-12-19 19:42:46.737171	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsadsa	dsad	dasd	dsad	\N	\N	40	2025-12-29 18:42:36.947026	1	2025-12-31 09:29:18.227189	1	t	f
3907	test	sdd	dsds	sdsd	file-sample_1MB.docx	uploads/attorneys/3e253036-7580-4791-aed4-eed850d910b5.docx	32	2025-12-19 20:13:13.387777	1	2025-12-31 09:29:18.227189	1	t	f
3907	test	amdin	dsd	ere	GLS Documentation.pdf	uploads/attorneys/860a49de-104c-405a-88a8-69a2cfae4335.pdf	31	2025-12-19 20:12:33.991749	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsad	dsad	dsad	dsad	\N	\N	43	2025-12-29 18:42:51.802443	1	2025-12-31 09:29:18.227189	1	t	f
3907	dsadsa	dsad	dasd	dsad	\N	\N	41	2025-12-29 18:42:36.960767	1	2025-12-31 09:29:18.227189	1	t	f
3907	Akshy	Sumrin	test	fd	\N	\N	35	2025-12-23 18:59:08.723468	1	2025-12-31 09:29:18.227189	1	t	f
3907	sad	sad	asd	sad	\N	\N	38	2025-12-29 18:31:48.874016	1	2025-12-31 09:29:18.227189	1	t	f
3907	sadsad	dsadas	dsadasd	dsad	\N	\N	39	2025-12-29 18:41:48.309149	1	2025-12-31 09:29:18.227189	1	t	f
3907	sdsada	dsadas	dsad	sadasd	\N	\N	45	2025-12-29 18:57:55.827131	1	2025-12-31 09:29:18.227189	1	t	f
3907	sdsada	dsadas	dsad	fdgdfg	\N	\N	44	2025-12-29 18:57:55.802271	1	2025-12-31 09:29:18.227189	1	t	f
3907	sfsdf	fdsf	fsdf	fsdf	\N	\N	49	2025-12-29 19:12:40.984301	1	2025-12-31 09:29:18.227189	1	t	f
3907	gfdgdfg	fdgfd	fdg	gfdg	file-sample_100kB.docx	uploads/attorneys/27fcec1e-d5b0-4555-986d-b12cc4896d45.docx	46	2025-12-29 19:04:03.060825	1	2025-12-31 09:29:18.227189	1	t	f
3907	m,m,jh	jhk	jhkjh	jhk	file-sample_1MB.docx	uploads/attorneys/b0e9e24d-b04d-4a39-8cf9-760c28af2f10.docx	50	2025-12-29 19:18:58.566537	1	2025-12-31 10:12:40.519002	1	f	f
3907	shubahm	dsad	dsad	dsad	file-sample_1MB.docx	uploads/attorneys/9ab7da91-c741-4ee9-b2c7-1b81d43b519e.docx	48	2025-12-29 19:11:52.848941	1	2025-12-31 10:12:40.519002	1	f	f
\.


--
-- Data for Name: billings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.billings (job_no, cancel_en_route, cancel_setup, billing_notes, videographer_hours_present, file_hours_length, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived, mark_is_done) FROM stdin;
3086	f	t	working that	4hrs	8hrs	1	2025-12-17 16:04:42.683959	1001	2025-12-17 17:09:57.332944	1001	t	f
3907	t	f	dsds	2hrs	7hrs	8	2025-12-19 16:12:19.542416	1	2025-12-31 09:29:18.235588	1	t	f
3086	t	f	working that	4hrs	8hrs	2	2025-12-17 16:07:13.494995	1001	2025-12-17 17:12:01.097072	1001	t	f
3907	t	f	ttest	4hrs	6hrs	9	2025-12-19 17:43:50.468224	1	2025-12-31 09:29:18.235588	1	t	f
3907	t	f	erewr	4hrs	6hrs	10	2025-12-19 19:32:09.502198	1	2025-12-31 09:29:18.235588	1	t	f
3086	t	f	still working	4hrs	8hrs	3	2025-12-17 16:09:44.425573	1001	2025-12-17 17:46:46.724897	1001	t	f
3086	t	f	wominh 	\N	\N	4	2025-12-17 16:19:00.006882	1001	2025-12-17 17:48:56.375293	1001	t	f
3907	t	f	info 	4hrs	6hrs	11	2025-12-19 20:14:01.821965	1	2025-12-31 09:29:18.235588	1	t	f
3086	t	f	adasd	\N	\N	5	2025-12-17 17:12:25.917578	1001	2025-12-17 17:56:17.974087	1001	t	f
3907	f	t	\N	\N	\N	14	2025-12-29 16:56:39.247717	1	2025-12-31 10:12:40.522992	1	f	f
3086	t	t	dsad	\N	\N	6	2025-12-17 18:15:17.464817	1001	2025-12-17 18:44:33.553571	1001	t	f
3295	t	f	\N	4hrs	6hrs	12	2025-12-22 20:38:22.859472	1001	2025-12-22 20:38:27.69819	1001	f	f
3106	t	f	dsdsdsd	23hrs	45hrs	13	2025-12-23 16:59:03.657714	1001	2025-12-23 16:59:03.657684	1001	f	f
3086	f	t	\N	\N	\N	7	2025-12-17 18:44:45.096294	1001	2025-12-29 17:53:17.600784	1001	t	f
3086	t	f	fghfghfgh	\N	\N	15	2025-12-29 18:02:15.964071	1001	2025-12-29 18:02:15.964047	1001	f	f
\.


--
-- Data for Name: cases; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cases (case_short_name, case_full_name, case_type, status, trial_date, id, entered_at, entered_by, last_modified_at, last_modified_by, case_no, is_archived, case_number, mark_is_done, progress_percentage, total_jobs, completed_jobs, case_status) FROM stdin;
AARON JONES vs ESTATE OF ELEANOR S. MASSELL	\N	Deposition	New	\N	37	2008-07-21 10:46:59.743	1001	2008-07-21 10:46:59.743	1001	1036	f	\N	f	\N	\N	\N	\N
ACE Fire Underwriters v. ALC Controls, et al.	\N	Deposition	New	\N	38	2008-07-21 10:47:22.977	1001	2008-07-24 16:52:22.94	1000	1037	f	\N	f	\N	\N	\N	\N
Zurich American Insurance Co. v. Myers Railroad Construction Co.	\N	Deposition	New	\N	39	2008-07-21 10:47:46.82	1001	2008-07-21 10:47:46.82	1001	1038	f	\N	f	\N	\N	\N	\N
Zachary Bowlin vs. Mary Miller and Rodney Miller	\N	Deposition	New	\N	40	2008-07-21 10:48:21.383	1001	2008-07-21 10:48:21.383	1001	1040	f	\N	f	\N	\N	\N	\N
Yvonne Amon Baldock vs. Susan Pound	\N	Deposition	New	\N	41	2008-07-21 10:48:39.15	1001	2008-07-21 10:48:39.15	1001	1041	f	\N	f	\N	\N	\N	\N
Yvetot Coquillon vs. Linda Mesko	\N	Deposition	New	\N	42	2008-07-21 10:48:50.447	1001	2008-07-21 10:48:50.447	1001	1042	f	\N	f	\N	\N	\N	\N
Yuyama Manfacturing Co Ltd v. JVM Co. Ltd.	\N	Deposition	New	\N	43	2008-07-21 10:49:44.353	1001	2008-07-21 10:49:44.353	1001	1043	f	\N	f	\N	\N	\N	\N
Yolanda A. Turman vs. Tire Kingdom et al. and Indemnity Ins. Co of N. America	\N	Deposition	New	\N	44	2008-07-21 10:50:08.697	1001	2008-07-21 10:50:08.697	1001	1044	f	\N	f	\N	\N	\N	\N
Wyatt, et al. v. Security Alarms Co., et al.	\N	Deposition	New	\N	45	2008-07-21 10:50:26.54	1001	2008-07-21 10:50:26.54	1001	1045	f	\N	f	\N	\N	\N	\N
Wyatt, et al. v. Security Alarms Co., et al.	\N	Deposition	New	\N	46	2008-07-21 10:50:43.9	1001	2008-07-21 10:50:43.9	1001	1046	f	\N	f	\N	\N	\N	\N
Wood vs.Four Seasons Development	\N	Deposition	New	\N	47	2008-07-21 10:51:49.48	1001	2008-07-24 15:58:19.403	1001	1047	f	\N	f	\N	\N	\N	\N
Wong v Buck, et al	\N	Deposition	New	\N	48	2008-07-21 10:52:07.637	1001	2008-07-21 10:52:07.637	1001	1048	f	\N	f	\N	\N	\N	\N
Williams vs. Big Lots	\N	Deposition	New	\N	49	2008-07-21 10:52:31.993	1001	2008-07-21 10:52:31.993	1001	1049	f	\N	f	\N	\N	\N	\N
William Thompson v. State Ethics Commission	\N	Deposition	New	\N	50	2008-07-21 10:52:44.963	1001	2008-07-21 10:52:44.963	1001	1050	f	\N	f	\N	\N	\N	\N
William Smith et al. vs. Lockheed Martin	\N	Deposition	New	\N	51	2008-07-21 10:52:59.98	1001	2008-07-24 15:46:31.24	1001	1051	f	\N	f	\N	\N	\N	\N
William Calvin Smith and Judy Smith vs. Wal-Mart	\N	Deposition	New	\N	52	2008-07-21 10:53:56.747	1001	2008-07-21 10:53:56.747	1001	1052	f	\N	f	\N	\N	\N	\N
William Barrera v. Kris International, LLC	\N	Deposition	New	\N	53	2008-07-21 10:54:26.277	1001	2008-07-21 10:54:26.277	1001	1054	f	\N	f	\N	\N	\N	\N
William Allen Tayler and Pickle Logging vs. Bruce Wrenn and Valley Pipeline, Inc	\N	Deposition	New	\N	54	2008-07-21 10:54:44.777	1001	2008-07-25 12:54:42.99	1000	1055	f	\N	f	\N	\N	\N	\N
Whitney National Bank v. Fidelity and Deposit Company of Maryland and Axis Surpl	\N	Deposition	New	\N	55	2008-07-21 10:54:57.433	1001	2008-07-21 10:54:57.433	1001	1056	f	\N	f	\N	\N	\N	\N
Whitefield Academy, Inc v Benjamin Pridemore and Mary Pridemore	\N	Deposition	New	\N	56	2008-07-21 10:55:15.713	1001	2008-07-21 10:55:15.713	1001	1057	f	\N	f	\N	\N	\N	\N
Wegrzyn vs. Vital Recovery Services	\N	Deposition	New	\N	57	2008-07-21 10:55:36.713	1001	2008-07-21 10:55:36.713	1001	1058	f	\N	f	\N	\N	\N	\N
Wanda Scott vs. Georgia Pacific	\N	Deposition	New	\N	58	2008-07-21 10:55:54.62	1001	2008-07-21 10:55:54.62	1001	1059	f	\N	f	\N	\N	\N	\N
Wanda Howard vs. Scott Tucker Contractors, Inc., et al.	\N	Deposition	New	\N	59	2008-07-21 10:56:10.777	1001	2008-07-21 10:56:10.777	1001	1060	f	\N	f	\N	\N	\N	\N
Waldrop vs. North American Property Corporation	\N	Deposition	New	\N	60	2008-07-21 10:56:26.01	1001	2008-07-21 10:56:26.01	1001	1061	f	\N	f	\N	\N	\N	\N
Quest Diagnostics v Clinica Sagrado	\N	Deposition	New	\N	35	2008-07-21 10:46:01.587	1001	2025-12-19 11:46:29.902866	1001	1034	f	36699	f	\N	\N	\N	\N
Michael Owens vs. Center Office Systems, Inc.	\N	Deposition	New	\N	36	2008-07-21 10:46:23.257	1001	2025-12-19 11:46:43.829211	1001	1035	f	222022	f	\N	\N	\N	\N
Johnson vs. Smith tes	\N	Deposition	New	\N	31	2008-07-21 10:42:52.99	1001	2025-12-19 20:08:12.950919	1001	1030	f	8585	f	\N	\N	\N	\N
Betty A. Davis v. Shari Diffley	\N	Deposition	New	\N	34	2008-07-21 10:43:53.913	1001	2025-12-22 18:02:12.909406	1001	1033	f	4545	f	\N	\N	\N	\N
Gonzalo Esparza v. Gold Creek Distributors, LLC	\N	Deposition	New	\N	32	2008-07-21 10:43:09.21	1001	2025-12-29 17:12:04.495889	1001	1031	f	567567	f	\N	\N	\N	\N
Valentin Daniel Lemoine v. Elise Agnes Chardon Lemoine	\N	Deposition	New	\N	33	2008-07-21 10:43:27.083	1001	2026-01-02 13:20:05.933716	1001	1032	f	1045	f	\N	\N	\N	\N
\.


--
-- Data for Name: equipment_time; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.equipment_time (job_no, laptop_used, pip_used, exhibit_tech, parking_cost, time_after, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived, mark_is_done) FROM stdin;
3086	t	f	f	0.00	18:17:00	1	2025-12-17 18:14:27.198478	1001	2025-12-17 18:27:34.773266	1001	t	f
3086	f	f	f	0.00	\N	2	2025-12-17 18:32:59.843749	1001	2025-12-17 18:33:09.085452	1001	t	f
3086	t	f	f	323.00	\N	3	2025-12-17 18:36:53.296734	1001	2025-12-17 18:37:00.72423	1001	t	f
3086	t	f	f	23.00	22:37:00	4	2025-12-17 18:37:25.792691	1001	2025-12-17 18:49:46.515753	1001	t	f
3086	t	f	f	323.00	03:23:00	5	2025-12-17 18:50:10.884953	1001	2025-12-17 18:54:01.860226	1001	t	f
3086	t	t	t	33333.00	22:54:00	6	2025-12-17 18:54:18.491781	1001	2025-12-17 18:59:44.490578	1001	t	f
3086	t	f	f	223.00	07:00:00	7	2025-12-17 19:00:46.973934	1001	2025-12-17 19:06:54.090726	1001	t	f
3086	f	f	f	33333.00	19:09:00	8	2025-12-17 19:07:07.05833	1001	2025-12-17 19:39:30.354292	1001	t	f
3086	t	f	f	555.00	23:39:00	9	2025-12-17 19:43:21.862299	1001	2025-12-17 19:59:23.811978	1001	t	f
3295	t	f	f	34.00	18:38:00	16	2025-12-22 20:38:56.870695	1001	2025-12-22 20:38:56.870654	1001	f	f
3106	t	f	f	56.00	06:06:00	17	2025-12-23 16:59:22.974172	1001	2025-12-23 16:59:22.974146	1001	f	f
3086	t	f	f	0.00	21:06:00	10	2025-12-17 19:59:38.573701	1001	2025-12-29 18:09:29.276057	1001	f	f
3907	t	t	f	32.00	16:17:00	11	2025-12-19 16:13:10.744086	1	2025-12-31 09:29:18.241405	1	t	f
3907	t	f	f	34.00	20:44:00	12	2025-12-19 17:44:39.178422	1	2025-12-31 09:29:18.241405	1	t	f
3907	t	f	f	23.00	20:45:00	13	2025-12-19 17:45:21.994269	1	2025-12-31 09:29:18.241405	1	t	f
3907	t	f	f	5.00	19:34:00	14	2025-12-19 19:33:08.234617	1	2025-12-31 09:29:18.241405	1	t	f
3907	t	f	f	34.00	20:21:00	15	2025-12-19 20:18:15.088236	1	2025-12-31 09:29:18.241405	1	t	f
3907	t	t	t	0.00	\N	18	2025-12-29 19:17:05.052043	1	2025-12-31 10:12:40.528723	1	f	f
\.


--
-- Data for Name: job_assignments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.job_assignments (assigner_id, assignee_id, job_no, case_no, reason, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived) FROM stdin;
18	11	3907	1030	working	8	2025-12-31 09:29:18.249268	1	2025-12-31 09:29:18.249271	1	f
18	11	3907	1030	test working	9	2025-12-31 10:12:40.535077	18	2025-12-31 10:12:40.53508	18	f
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.jobs (job_date, start_time, end_time, timezone_no, status, case_no, job_type, scheduled_by_email, job_loc_name, job_loc_address, job_loc_city, job_loc_state, job_loc_zip, scheduling_notes_html, zoom_meeting_id, confirmation_notes_html, cancel_by, cancel_date, id, entered_at, entered_by, last_modified_at, last_modified_by, job_no, cancel_details, cancel_resone, computed_status, is_archived, actual_session_start_time, actual_session_end_time, session_duration, session_completed, mark_is_done, video_upload_deadline, expected_video_count, mark_is_done_case, mark_is_done_witnesses, mark_is_done_attorneys, mark_is_done_billings, mark_is_done_equipment_time) FROM stdin;
2026-01-01 00:00:00	10:00:00	23:00:00	1017	Billed	1035	821	\N	Georgia Department of Human Resources - Offices of Regulatory Services	2 Peachtree Street, NW, Suite 32.494	Atlanta	GA	30303	\N	\N	\N	\N	\N	45	2009-04-28 14:33:54.31	1001	2026-01-02 10:11:34.703988	1001	4100	\N	\N	Session not started	f	2025-12-24 17:56:27.015122	2025-12-24 17:56:30.87541	00:00:03	f	f	\N	\N	t	f	f	f	f
2025-12-30 00:00:00	10:00:00	12:00:00	1017	Billed	1034	821	\N	Georgia Department of Human Resources - Offices of Regulatory Services	\N	\N	\N	\N	\N	\N	\N	1001	2025-12-23 20:40:24.157111	44	2008-10-14 14:45:14.41	1001	2025-12-23 15:10:24.161142	1001	3295	fdgdfgdfgdfgdfgdfg	JUDGE_ABSENT	Cancelled	f	2025-12-22 18:14:04.972594	2025-12-22 20:39:05.01802	02:25:00	f	f	\N	\N	f	f	f	f	f
2025-12-31 00:00:00	10:30:00	12:00:00	1017	Billed	1030	821	\N	ABF Offices	1165 Wilburn Road	Conley	GA	\N	\N	\N	\N	\N	\N	40	2009-03-20 15:14:02.323	1	2025-12-31 10:12:40.504413	1	3907	\N	\N	Session not started	f	2025-12-30 19:48:58.66737	2025-12-30 20:57:08.065137	01:08:09	f	f	\N	\N	t	f	t	t	t
2025-12-30 00:00:00	15:00:00	19:00:00	1017	Billed	1031	821	\N	Resurgens Orthopedics	5665 Peachtree Dunwoody Road, Ste 700	Atlanta	GA	\N	\N	\N	\N	\N	\N	41	2008-08-18 14:58:00.58	1001	2025-12-29 12:48:22.608081	1000	3086	\N	\N	Session not started	f	2025-12-29 18:07:21.088761	2025-12-29 18:18:22.606453	00:11:01	f	f	\N	\N	f	f	f	f	f
2025-12-29 00:00:00	13:10:00	14:37:00	1017	Billed	1033	821	\N	North Fayette Family Practice	\N	\N	\N	\N	\N	\N	\N	\N	\N	42	2008-08-21 17:07:04.44	1001	2025-12-23 11:29:34.366535	1001	3106	\N	\N	Completed	f	2025-12-22 14:23:21.561638	2025-12-23 16:59:34.364658	26:36:12	t	f	\N	\N	f	f	f	f	f
2025-12-31 00:00:00	17:30:00	18:30:00	1017	Billed	1032	821	\N	Resurgens Orthopaedics - Sandy Springs	5671 Peachtree Dunwoody Road\n\nSuite 900	Atlanta	GA	30342	\N	\N	\N	\N	\N	43	2009-05-28 13:49:37.203	1001	2025-12-31 10:28:43.675205	1001	4294	\N	\N	Session Started	f	2025-12-31 15:58:43.671204	\N	\N	f	f	\N	\N	f	f	f	f	f
\.


--
-- Data for Name: repositories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.repositories (wit_no, file_name, repository_level, file_path, job_no, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (full_name, email, login_name, login_password, profile_image_url, id, entered_at, last_modified_at, entered_by, last_modified_by, require_password_change, is_archived) FROM stdin;
Administrator		Administrator	\\x635347617935596f4f3577642f4666566c6f6644522f3232674e35554236696f74575a30646d486d49484c76333446347a4161672f4a6c626963767536654d442f724f5177787661566745576e64583638526d6346413d3d	\N	11	2006-04-11 13:59:21.947	2019-06-06 19:46:37.887	1	1001	\N	f
Heather Grau	HeatherG@GeorgiaReporting.com	heather	\\x2f484e72523662333353645759647a6f67434c45625061754b354a754755696c2f4e342f6c4d6c6f6b436a54755a582f6d2f394378384270476d6941415267665346424e4b316b7853477355347762704b31595341413d3d	\N	12	2008-07-20 12:48:44.55	2021-10-26 12:25:30.41	1	1001	\N	f
Amit Pachuri	amit1.p@cisinlabs.com	amit.p@cisinlabs.com	\\x8ad17dadafdf341124084e302023fc75bc5cf7b265b7ff84e383a5da182aa7f48d70e9e70b96b0045c10c911dadbcff9817ab7b1760c5366e6df3f33af5fc51c	uploads/profile_pictures/55d99c19-d83e-4d65-bb06-041e6dd0538b.jpg	18	2025-11-12 10:16:47.243	2025-12-19 20:23:49.224202	1001	1001	f	f
\.


--
-- Data for Name: witness_videos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.witness_videos (wit_no, job_no, start_time, end_time, file_name, file_path, id, entered_at, entered_by, last_modified_at, last_modified_by, is_archived) FROM stdin;
47	3907	20:25:00	20:25:00	\N	\N	32	2025-12-19 13:55:27.771158	1	2025-12-31 09:29:18.220005	1	t
30	3907	17:11:00	17:10:00	New Tab.mp4	uploads/witness_videos/6057f55e-9499-4e13-be24-8cb8d614936d.mp4	8	2025-12-18 11:40:50.692126	1	2025-12-31 09:29:18.220005	1	t
30	3907	17:26:00	17:27:00	New Tab.mp4	uploads/witness_videos/8e0fbed6-14dc-4751-acbe-9f2bdd1fd694.mp4	9	2025-12-18 11:55:32.666768	1	2025-12-31 09:29:18.220005	1	t
30	3907	17:26:00	17:27:00	\N	\N	10	2025-12-18 11:55:42.935248	1	2025-12-31 09:29:18.220005	1	t
33	3907	15:46:00	14:47:00	New Tab.mp4	uploads/witness_videos/65dfde20-156a-421c-aec2-4e94814091b6.mp4	18	2025-12-19 09:16:54.806805	1	2025-12-31 09:29:18.220005	1	t
25	3086	16:33:00	15:34:00	FAST API - Swagger UI.mp4	uploads/witness_videos/4923cada-ea64-4d13-a119-33aafa74271f.mp4	6	2025-12-18 11:11:14.908922	0	2025-12-18 11:38:39.542483	1001	t
25	3086	16:33:00	15:34:00	FAST API - Swagger UI.mp4	uploads/witness_videos/6225583b-2d76-4873-8eec-30ed27b90170.mp4	7	2025-12-18 11:38:39.542483	1001	2025-12-18 11:56:46.168378	1001	t
25	3086	16:33:00	15:34:00	New Tab.mp4	uploads/witness_videos/926ebe3e-731d-451a-a950-335cdcdd8265.mp4	11	2025-12-18 11:56:46.168378	1001	2025-12-18 11:57:00.076152	1001	t
25	3086	17:28:00	17:28:00	\N	\N	12	2025-12-18 11:57:24.835648	1001	2025-12-18 12:11:04.736676	1001	t
33	3907	15:46:00	14:47:00	\N	\N	19	2025-12-19 09:18:50.068012	1	2025-12-31 09:29:18.220005	1	t
40	3907	17:07:00	17:07:00	New Tab.mp4	uploads/witness_videos/8f814b0f-ac61-4d3f-afd8-84250e6a62d9.mp4	21	2025-12-19 11:36:14.175405	1	2025-12-31 09:29:18.220005	1	t
40	3907	17:06:00	17:06:00	New Tab.mp4	uploads/witness_videos/f2968015-74de-40af-9d71-29b93b3173cd.mp4	20	2025-12-19 11:35:22.386664	1	2025-12-31 09:29:18.220005	1	t
31	3086	17:56:00	17:55:00	New Tab.mp4	uploads/witness_videos/0d1d6b59-5ec1-4db4-9199-dd96869298a4.mp4	16	2025-12-18 12:26:18.512667	1001	2025-12-18 12:34:08.8323	1001	t
40	3907	17:07:00	17:07:00	Create Next App.mp4	uploads/witness_videos/730bcc29-287b-461d-aeac-4d9bc7a67577.mp4	23	2025-12-19 11:37:09.64907	1	2025-12-31 09:29:18.220005	1	t
49	3295	20:23:00	20:25:00	Create Next App.mp4	uploads/witness_videos/8fdbf8f6-796f-40a3-abf2-b5a75086538d.mp4	36	2025-12-22 14:52:35.97448	1001	2025-12-22 14:52:58.711211	1001	f
51	3106	09:57:00	10:57:00	Create Next App.mp4	uploads/witness_videos/e65dc4f5-3e18-4fe8-be91-3b01f5208d71.mp4	39	2025-12-23 11:28:02.791954	1001	2025-12-23 11:46:37.623256	1001	f
51	3106	09:57:00	09:57:00	FAST API - Swagger UI.mp4	uploads/witness_videos/fa3c3bd9-1ea9-4a4f-8210-38f005281533.mp4	40	2025-12-23 11:28:02.791954	1001	2025-12-23 11:46:37.623256	1001	f
49	3295	05:23:00	07:22:00	FAST API - Swagger UI.mp4	uploads/witness_videos/05b2c8bf-70ce-44fa-bd2f-9cec75fe71f2.mp4	37	2025-12-22 14:52:58.711211	1001	2025-12-22 14:52:58.711211	1001	f
31	3086	19:54:00	17:55:00	New Tab.mp4	uploads/witness_videos/44e90b6c-8e56-4dd6-a8fb-34d7e4638bd9.mp4	14	2025-12-18 12:26:18.512667	1001	2025-12-29 12:00:20.436251	1001	t
52	3106	19:15:00	17:18:00	Create Next App.mp4	uploads/witness_videos/f015f3db-9e33-4ecd-97e4-87c555ae80b9.mp4	42	2025-12-23 11:46:02.243812	1001	2025-12-23 11:46:02.243812	1001	f
51	3106	11:57:00	12:57:00	FAST API - Swagger UI.mp4	uploads/witness_videos/482218c0-e1e4-4681-841e-178a1784d94c.mp4	41	2025-12-23 11:28:02.791954	1001	2025-12-23 11:46:37.623256	1001	t
31	3086	17:54:00	18:54:00	New Tab.mp4	uploads/witness_videos/542ebfab-ecff-4383-9b36-91b593b67e55.mp4	13	2025-12-18 12:26:18.512667	1001	2025-12-29 12:00:20.436251	1001	t
48	3907	20:10:00	20:10:00	Create Next App.mp4	uploads/witness_videos/5d7edb2a-0bf2-4ca4-bc99-23dbfc3aea14.mp4	33	2025-12-19 14:39:39.53827	1	2025-12-31 09:29:18.220005	1	t
31	3086	17:55:00	17:55:00	New Tab.mp4	uploads/witness_videos/ee1fa039-d631-4b86-b183-ee64a7f88ac1.mp4	17	2025-12-18 12:26:18.512667	1001	2025-12-29 12:00:20.436251	1001	t
40	3907	17:07:00	17:07:00	New Tab.mp4	uploads/witness_videos/4a3d0e33-7253-49ee-b5f0-2ec198770b12.mp4	22	2025-12-19 11:36:26.673277	1	2025-12-31 09:29:18.220005	1	t
31	3086	17:56:00	19:54:00	FAST API - Swagger UI.mp4	uploads/witness_videos/77d803d7-fb44-46ca-beb3-7999e8fa9a02.mp4	15	2025-12-18 12:26:18.512667	1001	2025-12-29 12:01:15.125118	1001	t
41	3907	18:16:00	17:18:00	New Tab.mp4	uploads/witness_videos/92325fb6-bbcb-4bc2-802e-d15ea18f8991.mp4	24	2025-12-19 11:46:49.518429	1	2025-12-31 09:29:18.220005	1	t
41	3907	18:16:00	17:18:00	Create Next App.mp4	uploads/witness_videos/01aa2808-e25e-4852-be1b-64c6fe279ce0.mp4	25	2025-12-19 11:47:54.697036	1	2025-12-31 09:29:18.220005	1	t
41	3907	17:21:00	17:21:00	Create Next App.mp4	uploads/witness_videos/d0c4fca6-8fd5-4e1c-815a-3dec22bf28e7.mp4	26	2025-12-19 11:50:02.404207	1	2025-12-31 09:29:18.220005	1	t
44	3907	18:30:00	17:31:00	New Tab.mp4	uploads/witness_videos/43fa4362-f8f2-44e7-88ee-900bf009312a.mp4	27	2025-12-19 12:00:07.351069	1	2025-12-31 09:29:18.220005	1	t
45	3907	18:37:00	18:37:00	Create Next App.mp4	uploads/witness_videos/e21d48b7-2600-423b-99f0-ec901080bbbf.mp4	28	2025-12-19 12:07:26.635951	1	2025-12-31 09:29:18.220005	1	t
46	3907	17:39:00	17:39:00	New Tab.mp4	uploads/witness_videos/758f321c-92d9-4c75-be6f-c33cec0aa0be.mp4	29	2025-12-19 12:08:30.730269	1	2025-12-31 09:29:18.220005	1	t
48	3907	20:10:00	22:10:00	FAST API - Swagger UI.mp4	uploads/witness_videos/af872b23-8e2d-4739-bffb-9c143ff96022.mp4	34	2025-12-19 14:40:31.897266	1	2025-12-31 09:29:18.220005	1	t
47	3907	19:20:00	19:20:00	FAST API - Swagger UI.mp4	uploads/witness_videos/35da39da-8593-4f83-8368-8d9fe1815f2a.mp4	30	2025-12-19 13:49:23.738275	1	2025-12-31 09:29:18.220005	1	t
47	3907	19:20:00	19:20:00	FAST API - Swagger UI.mp4	uploads/witness_videos/0b776b44-ea72-460c-9b77-0f46677a8877.mp4	31	2025-12-19 13:55:09.405169	1	2025-12-31 09:29:18.220005	1	t
48	3907	20:10:00	22:10:00	FAST API - Swagger UI.mp4	uploads/witness_videos/7f0c2315-b1c2-4e3c-8dd0-cc47f70ea7b9.mp4	35	2025-12-19 14:41:28.893756	1	2025-12-31 09:29:18.220005	1	t
48	3907	17:55:00	16:56:00	Create Next App.mp4	uploads/witness_videos/cfbc96bb-cc20-48c1-a192-d4512826c290.mp4	38	2025-12-23 11:25:53.084791	1	2025-12-31 09:29:18.220005	1	t
55	3086	18:56:00	18:56:00	Create Next App.mp4	uploads/witness_videos/fe63768b-921b-4861-8a7e-a2ccef317952.mp4	43	2025-12-31 13:25:30.653434	1001	2025-12-31 13:25:30.653434	1001	f
\.


--
-- Data for Name: witnesses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.witnesses (witness_name, witness_email, actual_start_time, actual_end_time, read_sign_date, read_sign_to, id, entered_at, entered_by, last_modified_at, last_modified_by, wit_no, job_no, read_on_text, read_off_text, read_on_time, read_off_time, is_archived, mark_is_done) FROM stdin;
admin test	\N	\N	\N	\N	\N	34	2025-12-19 16:05:34.347553	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of admin test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of admin test	\N	\N	t	f
shubham	\N	\N	\N	\N	\N	23	2025-12-18 13:25:03.067971	1001	2025-12-18 12:10:41.926782	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of shubham in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of shubham	\N	\N	t	f
test	\N	\N	\N	\N	\N	29	2025-12-18 16:46:38.896442	1001	2025-12-18 12:10:46.216803	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of test	\N	\N	t	f
sas	\N	\N	\N	\N	\N	28	2025-12-18 14:14:08.679106	1001	2025-12-18 12:10:49.008749	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of sas in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of sas	\N	\N	t	f
devendra	\N	\N	\N	\N	\N	24	2025-12-18 13:59:20.404532	0	2025-12-18 12:10:51.268331	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of devendra in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of devendra	\N	\N	t	f
jose	\N	\N	\N	\N	\N	27	2025-12-18 14:13:10.398143	1001	2025-12-18 12:10:54.36135	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of jose in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of jose	\N	\N	t	f
devendra	\N	\N	\N	\N	\N	26	2025-12-18 13:59:20.522046	0	2025-12-18 12:10:56.832763	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of devendra in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of devendra	\N	\N	t	f
devendra	\N	\N	\N	\N	\N	25	2025-12-18 13:59:20.472853	0	2025-12-18 12:11:04.736676	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of devendra in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of devendra	15:31:00	15:32:00	t	f
shubhamcr	\N	\N	\N	\N	\N	31	2025-12-18 17:41:14.332325	1001	2025-12-29 12:01:15.125118	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of shubham in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of shubham	17:57:00	19:58:00	t	f
James	\N	\N	\N	\N	\N	52	2025-12-23 17:15:02.286673	1001	2025-12-23 11:46:02.243812	1001	\N	3106	We are now on the record at [Time] on [Date]. This is the [Type] deposition of James in the matter of Betty A. Davis v. Shari Diffley case number 4545	We are now off the record at [Time]. This concludes the deposition of James	18:15:00	17:16:00	f	f
Tom	\N	\N	\N	\N	\N	51	2025-12-23 16:56:17.358856	1001	2025-12-23 11:46:37.623256	1001	\N	3106	We are now on the record at [Time] on [Date]. This is the [Type] deposition of Tom in the matter of Betty A. Davis v. Shari Diffley case number 4545	We are now off the record at [Time]. This concludes the deposition of Tom	17:57:00	18:57:00	f	f
sgvhh	\N	\N	\N	\N	\N	53	2025-12-24 13:46:55.039469	1001	2025-12-24 12:23:21.331784	1001	\N	4100	We are now on the record at [Time] on [Date]. This is the [Type] deposition of sgvhh in the matter of Michael Owens vs. Center Office Systems, Inc. case number 222022	We are now off the record at [Time]. This concludes the deposition of sgvhh	\N	\N	t	f
devendra	\N	\N	\N	\N	\N	54	2025-12-29 17:30:48.546269	1001	2025-12-29 12:01:18.246135	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of devendra in the matter of Gonzalo Esparza v. Gold Creek Distributors, LLC case number 567567	We are now off the record at [Time]. This concludes the deposition of devendra	\N	\N	t	f
shubham	\N	\N	\N	\N	\N	49	2025-12-22 20:21:29.181631	1001	2025-12-22 14:52:58.711211	1001	\N	3295	We are now on the record at [Time] on [Date]. This is the [Type] deposition of shubham in the matter of Quest Diagnostics v Clinica Sagrado case number 36699	We are now off the record at [Time]. This concludes the deposition of shubham	20:22:00	23:22:00	f	f
sahil	\N	\N	\N	\N	\N	50	2025-12-22 20:24:16.998614	1001	2025-12-22 14:54:46.570854	1001	\N	3295	We are now on the record at [Time] on [Date]. This is the [Type] deposition of sahil in the matter of Quest Diagnostics v Clinica Sagrado case number 36699	We are now off the record at [Time]. This concludes the deposition of sahil	20:25:00	16:24:00	f	f
martin	\N	\N	\N	\N	\N	47	2025-12-19 19:18:29.237722	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of test	20:19:00	19:20:00	t	f
martin	\N	\N	\N	\N	\N	48	2025-12-19 20:08:42.813888	1	2025-12-31 10:12:40.507179	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of martin in the matter of Johnson vs. Smith tes case number 8585	We are now off the record at [Time]. This concludes the deposition of martin	20:10:00	20:10:00	f	f
sahil vr	\N	\N	\N	\N	\N	55	2025-12-29 17:31:27.594127	1001	2025-12-31 13:25:30.653434	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of sahil vr in the matter of Gonzalo Esparza v. Gold Creek Distributors, LLC case number 567567	We are now off the record at [Time]. This concludes the deposition of sahil vr	18:56:00	18:55:00	f	f
sahil	\N	\N	\N	\N	\N	30	2025-12-18 17:09:08.060549	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of sahil in the matter of Daniels v. IRS case number 43434	We are now off the record at [Time]. This concludes the deposition of sahil	17:12:00	17:12:00	t	f
admin test	\N	\N	\N	\N	\N	40	2025-12-19 17:04:57.55682	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of admin test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of admin test	17:06:00	17:06:00	t	f
test	\N	\N	\N	\N	\N	36	2025-12-19 16:09:39.172977	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of test	\N	\N	t	f
test	\N	\N	\N	\N	\N	32	2025-12-19 14:35:38.673661	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of test	\N	\N	t	f
dev	\N	\N	\N	\N	\N	35	2025-12-19 16:08:35.369877	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of dev in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of dev	\N	\N	t	f
test admin	\N	\N	\N	\N	\N	37	2025-12-19 16:49:14.107246	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test admin in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of test admin	\N	\N	t	f
test	\N	\N	\N	\N	\N	33	2025-12-19 14:45:54.23655	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of test	14:47:00	16:46:00	t	f
admin test	\N	\N	\N	\N	\N	38	2025-12-19 16:55:01.369828	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of admin test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of admin test	\N	\N	t	f
admin	\N	\N	\N	\N	\N	39	2025-12-19 16:57:28.454796	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of admin in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of admin	\N	\N	t	f
Martin	\N	\N	\N	\N	\N	42	2025-12-19 17:23:57.846443	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of Martin in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of Martin	\N	\N	t	f
martin	\N	\N	\N	\N	\N	43	2025-12-19 17:25:12.867095	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of martin in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of martin	\N	\N	t	f
admin test	\N	\N	\N	\N	\N	41	2025-12-19 17:15:31.497727	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of admin test in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of admin test	17:17:00	17:17:00	t	f
martin	\N	\N	\N	\N	\N	44	2025-12-19 17:26:49.536111	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of martin in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of martin	17:30:00	17:30:00	t	f
Tom	\N	\N	\N	\N	\N	46	2025-12-19 17:38:10.576329	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of Tom in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of Tom	17:39:00	17:39:00	t	f
martin dev	\N	\N	\N	\N	\N	45	2025-12-19 17:36:14.062987	1	2025-12-31 09:29:18.215425	1	\N	3907	We are now on the record at [Time] on [Date]. This is the [Type] deposition of martin in the matter of Johnson vs. Smith case number 43434	We are now off the record at [Time]. This concludes the deposition of martin	17:37:00	18:36:00	t	f
sdsd	\N	\N	\N	\N	\N	56	2025-12-31 16:31:25.670133	1001	2025-12-31 16:31:25.670096	1001	\N	4294	We are now on the record at [Time] on [Date]. This is the [Type] deposition of sdsd in the matter of Valentin Daniel Lemoine v. Elise Agnes Chardon Lemoine case number None	We are now off the record at [Time]. This concludes the deposition of sdsd	\N	\N	f	f
test	\N	\N	\N	\N	\N	57	2025-12-31 18:55:49.373662	1001	2025-12-31 18:55:49.373594	1001	\N	3086	We are now on the record at [Time] on [Date]. This is the [Type] deposition of test in the matter of Gonzalo Esparza v. Gold Creek Distributors, LLC case number 567567	We are now off the record at [Time]. This concludes the deposition of test	\N	\N	f	f
\.


--
-- Name: additional_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.additional_documents_id_seq', 40, true);


--
-- Name: attorneys_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.attorneys_id_seq', 50, true);


--
-- Name: billings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.billings_id_seq', 15, true);


--
-- Name: cases_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.cases_id_seq', 60, true);


--
-- Name: equipment_time_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.equipment_time_id_seq', 18, true);


--
-- Name: job_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.job_assignments_id_seq', 9, true);


--
-- Name: jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.jobs_id_seq', 45, true);


--
-- Name: repositories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.repositories_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 18, true);


--
-- Name: witness_videos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.witness_videos_id_seq', 43, true);


--
-- Name: witnesses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.witnesses_id_seq', 57, true);


--
-- Name: additional_documents additional_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.additional_documents
    ADD CONSTRAINT additional_documents_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attorneys attorneys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attorneys
    ADD CONSTRAINT attorneys_pkey PRIMARY KEY (id);


--
-- Name: billings billings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.billings
    ADD CONSTRAINT billings_pkey PRIMARY KEY (id);


--
-- Name: cases cases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT cases_pkey PRIMARY KEY (id);


--
-- Name: equipment_time equipment_time_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.equipment_time
    ADD CONSTRAINT equipment_time_pkey PRIMARY KEY (id);


--
-- Name: job_assignments job_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: repositories repositories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.repositories
    ADD CONSTRAINT repositories_pkey PRIMARY KEY (id);


--
-- Name: cases uq_cases_case_no; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT uq_cases_case_no UNIQUE (case_no);


--
-- Name: jobs uq_jobs_job_no; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT uq_jobs_job_no UNIQUE (job_no);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: witness_videos witness_videos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witness_videos
    ADD CONSTRAINT witness_videos_pkey PRIMARY KEY (id);


--
-- Name: witnesses witnesses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witnesses
    ADD CONSTRAINT witnesses_pkey PRIMARY KEY (id);


--
-- Name: ix_additional_documents_billing_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_additional_documents_billing_id ON public.additional_documents USING btree (billing_id);


--
-- Name: ix_additional_documents_equipment_time_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_additional_documents_equipment_time_id ON public.additional_documents USING btree (equipment_time_id);


--
-- Name: ix_additional_documents_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_additional_documents_id ON public.additional_documents USING btree (id);


--
-- Name: ix_additional_documents_job_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_additional_documents_job_no ON public.additional_documents USING btree (job_no);


--
-- Name: ix_attorneys_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attorneys_id ON public.attorneys USING btree (id);


--
-- Name: ix_attorneys_job_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attorneys_job_no ON public.attorneys USING btree (job_no);


--
-- Name: ix_billings_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_billings_id ON public.billings USING btree (id);


--
-- Name: ix_billings_job_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_billings_job_no ON public.billings USING btree (job_no);


--
-- Name: ix_cases_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_cases_id ON public.cases USING btree (id);


--
-- Name: ix_equipment_time_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_equipment_time_id ON public.equipment_time USING btree (id);


--
-- Name: ix_equipment_time_job_no; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_equipment_time_job_no ON public.equipment_time USING btree (job_no);


--
-- Name: ix_job_assignments_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_job_assignments_id ON public.job_assignments USING btree (id);


--
-- Name: ix_jobs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_jobs_id ON public.jobs USING btree (id);


--
-- Name: ix_repositories_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_repositories_id ON public.repositories USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_login_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_login_name ON public.users USING btree (login_name);


--
-- Name: ix_witness_videos_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_witness_videos_id ON public.witness_videos USING btree (id);


--
-- Name: ix_witnesses_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_witnesses_id ON public.witnesses USING btree (id);


--
-- Name: additional_documents additional_documents_billing_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.additional_documents
    ADD CONSTRAINT additional_documents_billing_id_fkey FOREIGN KEY (billing_id) REFERENCES public.billings(id);


--
-- Name: additional_documents additional_documents_equipment_time_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.additional_documents
    ADD CONSTRAINT additional_documents_equipment_time_id_fkey FOREIGN KEY (equipment_time_id) REFERENCES public.equipment_time(id);


--
-- Name: additional_documents additional_documents_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.additional_documents
    ADD CONSTRAINT additional_documents_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: attorneys attorneys_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attorneys
    ADD CONSTRAINT attorneys_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: billings billings_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.billings
    ADD CONSTRAINT billings_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: equipment_time equipment_time_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.equipment_time
    ADD CONSTRAINT equipment_time_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: job_assignments job_assignments_assignee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_assignee_id_fkey FOREIGN KEY (assignee_id) REFERENCES public.users(id);


--
-- Name: job_assignments job_assignments_assigner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_assigner_id_fkey FOREIGN KEY (assigner_id) REFERENCES public.users(id);


--
-- Name: job_assignments job_assignments_case_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_case_no_fkey FOREIGN KEY (case_no) REFERENCES public.cases(case_no);


--
-- Name: job_assignments job_assignments_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: jobs jobs_case_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_case_no_fkey FOREIGN KEY (case_no) REFERENCES public.cases(case_no);


--
-- Name: witness_videos witness_videos_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witness_videos
    ADD CONSTRAINT witness_videos_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: witness_videos witness_videos_wit_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witness_videos
    ADD CONSTRAINT witness_videos_wit_no_fkey FOREIGN KEY (wit_no) REFERENCES public.witnesses(id) ON DELETE CASCADE;


--
-- Name: witnesses witnesses_job_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.witnesses
    ADD CONSTRAINT witnesses_job_no_fkey FOREIGN KEY (job_no) REFERENCES public.jobs(job_no);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict 3IPnf786KqN67iwDZYUJm5f9iK1osF7piq8CV15n4optAokiD2IUW7S2b0w011o

