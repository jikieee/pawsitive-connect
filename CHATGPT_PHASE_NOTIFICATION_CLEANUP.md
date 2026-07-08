# ChatGPT Phase: Notification Sidebar Cleanup

## Completed
- Removed the old top-right / floating notification dropdown from:
  - `templates/user_dashboard.html`
  - `templates/org_dashboard.html`
  - `templates/dashboard.html`
- Kept the topbar search area intact.
- Restored Organization Dashboard Settings to the existing shared account settings route:
  - `{% url 'profile_settings' %}`
- Updated notification badge handling so sidebar badges use `data-notif-count`.
- Updated `static/js/dashboard.js` so clicking the Notifications sidebar item opens the Notifications tab instead of toggling the removed dropdown.
- Removed dropdown-only JavaScript references from shared dashboard JS.
- Removed dropdown-only inline JavaScript from `org_dashboard.html` and `dashboard.html`.

## Notes
- I could not run Django checks/tests in this sandbox because Django is not installed in the execution environment.
- Please run these locally after extracting:

```powershell
py manage.py check
py manage.py test
```

## Manual Verification Checklist
- User dashboard: Notifications sidebar opens notification tab.
- User dashboard: no floating notification panel remains in the top-right.
- Org dashboard: Notifications sidebar opens notification tab.
- Org dashboard: no floating notification panel remains in the top-right.
- Org dashboard: Settings opens the shared account settings page.
- Admin dashboard: no top-right notification dropdown remains.
- Search bar remains visible in topbar.
- Logout remains visible in sidebar.
