# Supabase PostgreSQL Setup & Migration Guide

This document describes how to configure YACE to use a managed cloud PostgreSQL database hosted on Supabase instead of a local PostgreSQL installation.

## Step 1: Create a Supabase Project

1. Sign in or sign up at [Supabase](https://supabase.com/).
2. Click **New Project** and select your organization.
3. Choose a project name, database password, and region.
4. Click **Create new project** and wait for provisioning to complete.

## Step 2: Retrieve the Connection String

1. In the Supabase dashboard, navigate to **Project Settings** (gear icon in the sidebar) > **Database**.
2. Scroll down to the **Connection string** section.
3. Click the **URI** tab.
4. Copy the connection string. It will look like this:
   ```text
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres
   ```

## Step 3: Update `.env` File

Open your `.env` file in the root of the project and update the database settings:

```env
# Database Connections
DATABASE_PROVIDER=supabase

# Primary production/development database URL
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres

# Test database URL. Since we are on a free tier, we can use a separate database schema ('test_schema')
# in the exact same Supabase database. This satisfies YACE's safety check requiring different URLs.
TEST_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres?options=-c%20search_path=test_schema
```

*(Note: Replace `[YOUR-PASSWORD]` and `[YOUR-PROJECT-ID]` with your actual Supabase database password and project domain.)*

## Step 4: Run Database Migrations

Apply the database schema using Alembic to construct all the required tables in your Supabase project:

```bash
venv\Scripts\python -m alembic upgrade head
```

## Step 5: Verify the Connection

Execute the automated database health verification script to ensure connection, latency, table structure, and ORM mapping are functioning:

```bash
venv\Scripts\python scripts/test_database_connection.py
```

This will output details about the database connection and generate a report at `generated/reports/database_health_report.json`.

You can also run the migration validation script to verify that all tables were correctly provisioned:

```bash
venv\Scripts\python scripts/verify_migrations.py
```
This generates a report at `generated/reports/migration_validation_report.json`.
