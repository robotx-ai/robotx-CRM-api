-- Create sales lead follow-ups table (CRD support for sales lead notes)
-- Rollback guidance:
--   drop table if exists public.sales_lead_followups;
--   drop trigger if exists trg_sales_lead_followups_set_updated_at on public.sales_lead_followups;
--   drop function if exists public.set_updated_at();

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.sales_lead_followups (
  id uuid primary key default gen_random_uuid(),
  sales_lead_id uuid not null references public.sales_leads(id) on delete cascade,
  owner_user_id uuid not null references public.user_profiles(id),
  note text not null check (char_length(note) between 1 and 4000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_sales_lead_followups_sales_lead_id_created_at
  on public.sales_lead_followups (sales_lead_id, created_at desc);

create index if not exists idx_sales_lead_followups_owner_user_id
  on public.sales_lead_followups (owner_user_id);

drop trigger if exists trg_sales_lead_followups_set_updated_at on public.sales_lead_followups;
create trigger trg_sales_lead_followups_set_updated_at
before update on public.sales_lead_followups
for each row
execute function public.set_updated_at();
