# 🚨 Protocol Incident Report: mock_drift

- **ID**: INCIDENT-SAMPLE-001.md
- **Trace ID**: `fe-mock-7788`
- **Severity**: medium
- **Component**: `AuthModule`
- **Timestamp**: Mon Apr 13 03:17:55 2026

## 📝 Description
Detected a minor drift in the authentication token refresh logic.

## 🔍 Payload Analysis
### Data Sent (Frontend Request)
```json
{ "action": "refresh", "token_type": "bearer" }
```

### Data Received (Backend Response)
```json
{ "status": "ok", "next_cycle": 3600 }
```

---
*Targeted for automatic RCA by Governance Agent.*
