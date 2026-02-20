-- Seed mock follow-ups for leads in "Following Up" and "Lost" statuses.
-- Safe to run multiple times: notes are inserted only if they do not already exist
-- for the same sales lead.

insert into public.sales_lead_followups (sales_lead_id, owner_user_id, note)
select
  sl.id as sales_lead_id,
  sl.owner_user_id,
  seed.note
from public.sales_leads sl
cross join lateral (
  values
    ('Called customer and confirmed interest. Waiting for procurement sign-off.'),
    ('Sent follow-up email with pricing sheet and installation timeline.')
) as seed(note)
where sl.lead_status = 'Following Up'
  and not exists (
    select 1
    from public.sales_lead_followups f
    where f.sales_lead_id = sl.id
      and f.note = seed.note
  );

insert into public.sales_lead_followups (sales_lead_id, owner_user_id, note)
select
  sl.id as sales_lead_id,
  sl.owner_user_id,
  seed.note
from public.sales_leads sl
cross join lateral (
  values
    ('Marked as lost after budget freeze. Requested permission to reconnect next quarter.'),
    ('No response after three attempts. Closed as lost with competitor selected.')
) as seed(note)
where sl.lead_status = 'Lost'
  and not exists (
    select 1
    from public.sales_lead_followups f
    where f.sales_lead_id = sl.id
      and f.note = seed.note
  );
