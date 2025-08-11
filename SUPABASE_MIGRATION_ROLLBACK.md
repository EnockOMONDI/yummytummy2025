# 🔄 Supabase Migration Rollback Plan

## Quick Rollback to Neon PostgreSQL

If the Supabase migration encounters issues, use these commands to rollback:

### 1. Revert Database Connection

```bash
# Revert .env file
DATABASE_URL=postgresql://neondb_owner:npg_NG34ncVtzPIO@ep-solitary-fire-a2k5kc4y-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# Revert render.yaml
- key: DATABASE_URL
  value: "postgresql://neondb_owner:npg_NG34ncVtzPIO@ep-solitary-fire-a2k5kc4y-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
```

### 2. Test Local Connection

```bash
python manage.py check --database default
python manage.py migrate --dry-run
```

### 3. Redeploy to Render

```bash
git add .env render.yaml
git commit -m "rollback: revert to Neon PostgreSQL"
git push origin wearelive
```

### 4. Verify Rollback

- ✅ Database connection works
- ✅ M-Pesa integration functional
- ✅ Orders processing correctly
- ✅ Admin interface accessible
