# Sale Quote Approval Module

Multi-level quotation approval workflow based on **Total Amount** and **Total Cost**.

---

## 1. Installation

### Step 1: Start PostgreSQL
```bash
docker compose up -d db
```

### Step 2: Initialize the database
```bash
docker compose run --rm odoo odoo -d odoo -i base --stop-after-init
```

### Step 3: Start Odoo
```bash
docker compose up -d
```

### Step 4: Access the system
Open:

```text
http://localhost:8069
```

---

## 2. Service Management

### Start all services
```bash
docker compose up -d
```

### Stop all services
```bash
docker compose down
```

### Restart all services
```bash
docker compose restart
```

### Restart a specific service
```bash
docker compose restart odoo
docker compose restart db
```

### Check running containers
```bash
docker compose ps
```

### View all logs
```bash
docker compose logs -f
```

### View Odoo logs only
```bash
docker compose logs -f odoo
```

### View PostgreSQL logs only
```bash
docker compose logs -f db
```

---

## 3. Module Setup

1. Go to **Apps**
2. Click **Update Apps List**
3. Search for **Sale Quote Approval**
4. Install the module

---

## 4. Test Scenario

Create a product with defined **Cost** and **Sales Price**.

Then create quotations to verify these cases:

- **Full approval**: `Total Cost >= Total Amount`
- **Leader only**: `Total Amount <= Total Cost + 50% of Total Cost`
- **No approval**: `Total Amount > Total Cost + 50% of Total Cost`

Recommended test users:

- Sales Person
- Sales Team Leader
- Sales Manager
- Finance Manager

Assign the corresponding groups and test the approval flow end-to-end.

---

## 5. Run Automated Tests

```bash
docker compose run --rm odoo odoo -d test_db -i sale_quote_approval --test-enable --stop-after-init
```
