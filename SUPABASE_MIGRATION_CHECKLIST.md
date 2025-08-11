# ✅ Supabase Migration Checklist

## Pre-Migration Preparation
- [ ] **Backup Current Data**: Export from Neon PostgreSQL
- [ ] **Test Supabase Connection**: Verify credentials work
- [ ] **Review Migration Plan**: Understand all steps

## Data Migration
- [ ] **Export Neon Data**: `pg_dump` with custom format
- [ ] **Import to Supabase**: `pg_restore` with your connection string
- [ ] **Verify Data Integrity**: Check record counts match

## Configuration Updates
- [ ] **Update .env**: New Supabase DATABASE_URL
- [ ] **Update .env.example**: Template with Supabase format
- [ ] **Update render.yaml**: Production deployment config

## Local Testing
- [ ] **Database Connection**: `python manage.py check --database default`
- [ ] **Migration Status**: `python manage.py showmigrations`
- [ ] **Run Migrations**: `python manage.py migrate`
- [ ] **Create Superuser**: `python manage.py createsuperuser`
- [ ] **Test M-Pesa**: `python manage.py check_mpesa_health`
- [ ] **Data Verification**: Check Products, Orders, Categories counts

## Production Deployment
- [ ] **Commit Changes**: Git commit with descriptive message
- [ ] **Push to Branch**: `git push origin wearelive`
- [ ] **Monitor Deployment**: Watch Render build logs
- [ ] **Verify Live Site**: Test homepage, admin, M-Pesa

## Post-Migration Verification
- [ ] **Database Performance**: Check query response times
- [ ] **M-Pesa Integration**: Test payment flow
- [ ] **Order Processing**: Create test order
- [ ] **Email Notifications**: Verify emails send correctly
- [ ] **Admin Interface**: Test all admin functions

## Rollback Plan (If Needed)
- [ ] **Revert Configuration**: Use SUPABASE_MIGRATION_ROLLBACK.md
- [ ] **Test Rollback**: Verify Neon connection works
- [ ] **Redeploy**: Push rollback changes to production

## Success Criteria
- ✅ **Zero Downtime**: Site remains accessible during migration
- ✅ **Data Integrity**: All data migrated successfully
- ✅ **M-Pesa Functional**: Payment processing works
- ✅ **Performance**: Response times acceptable
- ✅ **Monitoring**: No error alerts post-migration
