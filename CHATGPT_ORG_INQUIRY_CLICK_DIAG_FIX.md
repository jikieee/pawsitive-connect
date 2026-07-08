# Org Adoption Inquiry Click Diagnostic Fix

## Issue confirmed
The Organization dashboard inquiry list was visually rendered, but the clickable behavior was unreliable because the list rows could render as plain `.msg-item` elements without dependable click metadata/behavior in the active runtime.

## Fix applied
- Replaced organization inquiry rows with real `<button type="button">` controls.
- Added explicit `data-open-inquiry` and `data-inquiry-id` attributes.
- Added inline fallback `onclick` that calls `openOrgInquiryThread(...)`.
- Rebuilt the thread switching function so it:
  - activates the clicked inquiry row,
  - hides all other panels,
  - removes `hidden` from the selected panel,
  - forces `display: block` only on the selected thread,
  - updates `aria-selected` and `aria-hidden`,
  - scrolls to the selected thread on mobile.
- Added mobile-friendly focus/tap styles.

## Validation
- Python syntax check: passed via `py_compile`.
- JavaScript syntax check: passed via `node --check`.
- Full Django `manage.py check/test` could not be run in the packaging environment because Django is not installed there. Run locally inside your `.venv`.

## Test path
1. Login as Rescue Organization.
2. Open Adoption Inquiries.
3. Click the second inquiry.
4. The selected thread panel should change immediately.
5. On mobile, tapping an inquiry should scroll down to the selected thread.
