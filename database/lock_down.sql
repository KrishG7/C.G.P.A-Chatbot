-- Run this ONLY AFTER SUPABASE_KEY in .env (and in your host's variables) is the service_role key
-- and you have confirmed the app works with it. The backend then bypasses RLS, so removing the
-- "allow everyone" policies closes the tables to anyone holding the public anon key.
-- Policy names are the ones found on the live project on 2026-10-28; check with:
--   select tablename, policyname from pg_policies where schemaname = 'public';
drop policy if exists "Enable read/write for all"       on public.chats;
drop policy if exists "Enable all access"               on public.students;
drop policy if exists "Enable all access"               on public.classes;
drop policy if exists "Enable all access"               on public.attendance_records;
drop policy if exists "Enable access for all users"     on public.conversations;
alter table public.chats               enable row level security;
alter table public.students            enable row level security;
alter table public.classes             enable row level security;
alter table public.attendance_records  enable row level security;
alter table public.conversations       enable row level security;
