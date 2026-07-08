# Phase 3 Mobile Stabilization Fixes

## Fixed
- Made notification mark-read endpoint defensive so empty notification IDs no longer crash `/api/notifications/mark-read/`.
- Changed Mark all as read frontend calls to send `all=1` instead of an empty `ids` value.
- Added actual file input support to the Organization Report Update modal so uploaded rescue photos are sent to the backend.
- When a report is marked `rescued`, report photos are now synced into the created/reused rescued animal gallery.
- Rescued animal cards/details can now use the uploaded rescue/report photos instead of falling back to dog/cat icons.
- Reworked Organization Adoption Inquiries into a two-pane layout: inquiry list on the left and only the selected thread on the right.
- Added working Grid/List toggle behavior for Organization rescued animal cards.
- Added mobile-friendly styling for inquiry threads, announcement images, report modal images, and Leaflet/modal stacking.

## Manual checks recommended
- Submit/update a report with rescue photos, mark it rescued, then confirm the image appears in Org Animals, User Browse Animals, Admin Animals, and detail modals.
- Click Mark all as read in User/Org/Admin notifications.
- Open Org Adoption Inquiries with two or more inquiries and verify only the selected thread displays.
- Test Grid/List buttons on Org Rescued Animals.
