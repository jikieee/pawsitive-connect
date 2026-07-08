# Phase 2 Admin + Export + Audit Enhancements

## Changes made

### Organization dashboard
- Added search and category filters to the Organization Notifications tab.
- Added working CSV export for organization rescue reports.
- Added CSV export for organization Rescue Activity chart data.

### Admin dashboard
- Added CSV export for admin report management.
- Added CSV export for the admin monthly activity chart.
- Added client-side pagination for long admin tables:
  - Users
  - Organizations
  - Reports
  - Animals
  - Announcements
  - Notifications
  - Audit Logs
- Added View Details modals for admin reports and rescued animals.
- Added an Admin Audit Logs tab.
- Added lightweight audit logging for:
  - user active/inactive toggles
  - rescue organization active/inactive toggles
  - report status updates
  - admin CSV exports

### User dashboard
- Added client-side pagination to Track Rescue Progress.
- Added client-side pagination to User Notifications.

## Files modified
- `core/models.py`
- `core/migrations/0006_adminauditlog.py`
- `core/views.py`
- `pawsitive_connect/urls.py`
- `organizations/views.py`
- `organizations/urls.py`
- `templates/dashboard.html`
- `templates/org_dashboard.html`
- `templates/user_dashboard.html`
- `static/css/dashboard.css`
- `static/css/user_dashboard.css`

## Validation
Commands run successfully:

```powershell
python manage.py check
python manage.py test
python manage.py migrate --noinput
```

Result:

```text
System check identified no issues.
Ran 24 tests — OK.
```

## Notes
- The new audit log requires the included migration: `core.0006_adminauditlog`.
- After extracting this version, run `python manage.py migrate` before testing the admin actions.
