# Phase 3.2 Final Polish Fixes

## Changes made

### 1. Image sizing optimization
- Added cross-role media sizing rules in `static/css/phase3_mobile.css`.
- Animal images, report photos, announcement photos, avatars, logos, and modal images now use consistent `object-fit: cover` behavior.
- Announcement images now have smaller max heights on desktop and mobile so they do not dominate the card layout.

### 2. Organization adoption inquiry thread behavior
- Added robust delegated JavaScript in `templates/org_dashboard.html`.
- Inquiry list items now reliably activate only their selected thread panel.
- Non-selected inquiry threads are hidden using both `.active` class and `hidden` attribute.
- The first inquiry is auto-selected when the page loads.

### 3. Admin notifications for new accounts
- Updated `core/views.py` registration flow.
- When a new reporter or rescue organization account is created, all admin users receive a notification.
- Notification includes the new user's name/username and selected role.

### 4. Admin report management clarity
- Updated the Admin Reports tab header to explicitly say it shows reports submitted by all accounts across the system.
- Existing admin report query already uses all `AnimalReport` records, so no restrictive filter was added.

### 5. Cache-busting
- Bumped dashboard static asset query strings to `phase3-mobile-fix3` so browsers load the updated CSS/JS.

## Validation
- `python -m py_compile core/views.py accounts/views.py organizations/views.py animals/views.py reports/views.py`
- `node --check static/js/dashboard.js`
- `node --check static/js/phase3_mobile.js`

All syntax checks passed in the sandbox.

## Recommended manual checks
1. Create a new reporter account and confirm an admin notification appears.
2. Create a new rescue organization account and confirm an admin notification appears.
3. Login as admin and confirm the Reports tab lists reports from all users.
4. Login as org with 2+ adoption inquiries and confirm clicking each inquiry opens only that thread.
5. Check announcement, animal, report, avatar, and logo images on desktop and mobile.
