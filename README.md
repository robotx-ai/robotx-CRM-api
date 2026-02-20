# robotx-CRM-api

FastAPI service for `machineproductlibrary` CRUD against Supabase.

## Run

```bash
cd /home/zhour/robotx/robotx-CRM-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open Swagger UI:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/openapi.json

## Env

The app loads env vars in this order:

1. `robotx-CRM-api/.env`
2. `robotx-CRM-api/.env.local`
3. `robotx-CRM/demo/.env.local`

Required:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Optional:

- `API_PREFIX` (default `/api/v1`)

## Main Endpoints

- `GET /api/v1/machine-product-library`
- `GET /api/v1/machine-product-library/{row_id}`
- `GET /api/v1/machine-product-library/by-sn/{sn_pid}`
- `POST /api/v1/machine-product-library`
- `PATCH /api/v1/machine-product-library/{row_id}`
- `DELETE /api/v1/machine-product-library/{row_id}`

## Store Management Endpoints

- `GET /api/v1/customerCenter/storeManagement`
- `GET /api/v1/customerCenter/storeManagement/agents/options`
- `GET /api/v1/customerCenter/storeManagement/{store_id}`
- `GET /api/v1/customerCenter/storeManagement/{store_id}/accounts`
- `POST /api/v1/customerCenter/storeManagement`
- `PATCH /api/v1/customerCenter/storeManagement/{store_id}`
- `DELETE /api/v1/customerCenter/storeManagement/{store_id}`

## Sales Leads Endpoints

- `GET /api/v1/customerCenter/salesLeads`
- `GET /api/v1/customerCenter/salesLeads/{lead_id}`
- `POST /api/v1/customerCenter/salesLeads`
- `PATCH /api/v1/customerCenter/salesLeads/{lead_id}`
- `DELETE /api/v1/customerCenter/salesLeads/{lead_id}`

## Sales Lead Follow-ups Endpoints

- `GET /api/v1/customerCenter/salesLeads/{lead_id}/followups`
- `GET /api/v1/customerCenter/salesLeads/{lead_id}/followups/{followup_id}`
- `POST /api/v1/customerCenter/salesLeads/{lead_id}/followups`
- `DELETE /api/v1/customerCenter/salesLeads/{lead_id}/followups/{followup_id}`

## SQL Scripts

- `sql/001_create_sales_lead_followups.sql`: creates `sales_lead_followups` table.
- `sql/002_seed_mock_sales_lead_followups.sql`: seeds mock follow-up notes for leads in
  `Following Up` and `Lost` statuses.
