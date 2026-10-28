-- C.G.P.A. database schema (PostgreSQL / Supabase).
-- Column names match the live Supabase project (read on 2026-10-28). Run this in the Supabase SQL
-- editor on a NEW project; on the existing project it is safe to re-run (everything is "if not exists").

create table if not exists classes (
    id            bigint generated always as identity primary key,
    created_at    timestamptz not null default now(),
    teacher_email text        not null,
    class_name    text        not null
);
create index if not exists classes_teacher_email_idx on classes (teacher_email);

create table if not exists students (
    id            bigint generated always as identity primary key,
    created_at    timestamptz not null default now(),
    teacher_email text,
    name          text   not null,
    student_id    text   not null,
    details       jsonb  not null default '{}'::jsonb,
    class_id      bigint not null references classes (id) on delete cascade
);
create index if not exists students_teacher_email_idx on students (teacher_email);
-- upsert(..., on_conflict="class_id, student_id") needs this unique constraint
create unique index if not exists students_class_student_uq on students (class_id, student_id);

create table if not exists attendance_records (
    id         bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    student_id text   not null,
    class_id   bigint not null references classes (id) on delete cascade,
    date       date   not null,
    status     text   not null
);
-- upsert(..., on_conflict="student_id, class_id, date") needs this unique constraint
create unique index if not exists attendance_student_class_date_uq on attendance_records (student_id, class_id, date);

create table if not exists conversations (
    id         bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    user_email text not null,
    role       text not null,
    message    text not null
);
create index if not exists conversations_user_email_idx on conversations (user_email, created_at);

-- Login roles. Supabase Auth stores the passwords; this table stores who may do what.
-- Only the backend (service_role key) can read or write it: RLS is on and there are no policies.
create table if not exists profiles (
    email      text primary key,                 -- always lower-case
    role       text    not null check (role in ('student', 'teacher', 'admin')),
    approved   boolean not null default false,   -- students are approved at signup, teachers by an admin
    created_at timestamptz not null default now()
);
alter table profiles enable row level security;

-- Create the first admin here (never through the app), then sign up with the same email in the app:
--   insert into profiles (email, role, approved) values ('you@example.com', 'admin', true);
