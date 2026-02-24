begin;

alter table if exists public.sales_leads
  add column if not exists organization_name text,
  add column if not exists customer_type text,
  add column if not exists address text,
  add column if not exists city text,
  add column if not exists state text,
  add column if not exists zip_code text,
  add column if not exists referrer_name text,
  add column if not exists referrer_phone text,
  add column if not exists referrer_email text;

update public.sales_leads
set organization_name = 'Unknown Organization'
where organization_name is null or btrim(organization_name) = '';

update public.sales_leads
set customer_type = 'Individual'
where customer_type is null or btrim(customer_type) = '';

update public.sales_leads
set address = location
where (address is null or btrim(address) = '')
  and location is not null
  and btrim(location) <> '';

alter table public.sales_leads
  alter column organization_name set default 'Unknown Organization',
  alter column organization_name set not null,
  alter column customer_type set default 'Individual',
  alter column customer_type set not null;

alter table public.sales_leads
  drop constraint if exists sales_leads_lead_source_check,
  drop constraint if exists sales_leads_lead_status_check,
  add constraint sales_leads_lead_source_check check (
    lead_source in ('Sales Email', 'Shopify Website', 'Referral', 'Manufacturer Referral')
  ),
  add constraint sales_leads_lead_status_check check (
    lead_status in (
      'Unfollowed',
      'Following Up',
      'Converted',
      'Lost',
      'Followed but No Reply',
      'Followed with Reply',
      'Sales Pending',
      'Sales Rejected'
    )
  ),
  add constraint sales_leads_customer_type_check check (
    customer_type in ('Education', 'Individual', 'Warehouse', 'Hotel', 'Hospital')
  );

create index if not exists sales_leads_customer_type_idx
  on public.sales_leads(customer_type);
create index if not exists sales_leads_organization_name_idx
  on public.sales_leads(organization_name);
create index if not exists sales_leads_city_idx
  on public.sales_leads(city);
create index if not exists sales_leads_state_idx
  on public.sales_leads(state);
create index if not exists sales_leads_zip_code_idx
  on public.sales_leads(zip_code);

alter table public.sales_leads
  drop column if exists location;

commit;
