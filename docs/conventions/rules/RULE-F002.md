# [RULE-F002]: Frontend-Backend API Contract

## 1. Unified Response Wrapper
- ALL backend API responses MUST be wrapped in the `ApiResponse` class.
- Frontend services MUST use the `ApiResponse<T>` type to parse responses.
- Success codes: HTTP 200/201.
- Message field in `ApiResponse` is for end-user display; `detail` or `error_code` is for internal debugging.

## 2. Authentication Enforcement
- All protected routes MUST use `Depends(get_current_user)`.
- Frontend MUST use the centralized `api` axios instance to ensure Bearer tokens are injected.
- Native `fetch` is FORBIDDEN except for beacons/telemetry with explicit token injection.

## 3. Error Handling
- Frontend MUST NOT crash on 401/403/500 errors.
- 401: Clear local tokens and redirect to `/login` (with redirect lock to prevent loops).
- 500: Display a non-disruptive notification and log to telemetry.
- Fail-safe defaults: If data fetching fails, use empty arrays/objects instead of undefined.

## 4. State Management Consistency
- `authStore` is the source of truth for user permissions.
- DO NOT derive roles or permissions from local metadata (like ID). Always wait for `/me` profile sync.
