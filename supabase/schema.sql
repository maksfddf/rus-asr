create extension if not exists pgcrypto;

create table if not exists public.jobs (
  id uuid primary key,
  title text,
  status text not null default 'queued',
  storage_path text not null,
  duration_s numeric,
  text text,
  srt text,
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

alter table public.jobs enable row level security;

drop policy if exists jobs_read on public.jobs;
create policy jobs_read on public.jobs for select using (true);

drop policy if exists jobs_insert on public.jobs;
create policy jobs_insert on public.jobs for insert with check (status = 'queued');

create index if not exists jobs_queue_idx on public.jobs (status, created_at);

create or replace function public.claim_job()
returns setof public.jobs
language sql
security definer
set search_path = public
as $$
  update public.jobs
     set status = 'running', started_at = now()
   where id = (
     select id from public.jobs
      where status = 'queued'
      order by created_at
      limit 1
      for update skip locked
   )
  returning *;
$$;

grant execute on function public.claim_job() to service_role, anon;

insert into storage.buckets (id, name, public)
values ('audio', 'audio', false)
on conflict (id) do nothing;

drop policy if exists audio_insert on storage.objects;
create policy audio_insert on storage.objects
  for insert to anon with check (bucket_id = 'audio');

drop policy if exists audio_read on storage.objects;
create policy audio_read on storage.objects
  for select to anon using (bucket_id = 'audio');
