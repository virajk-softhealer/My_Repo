# Webhook Implementation: Comprehensive Test Plan

This document outlines the standard test cases for validating both Inbound and Outbound webhooks in Odoo 19.

---

## 🛰️ 1. Outbound Webhook Test Cases (Odoo to External)

### Test Case 1.1: Basic Record Synchronization
- **Scenario**: Sync a new Contact to an external system.
- **Prerequisites**: Webhook configured for `res.partner` on `Create`.
- **Steps**:
    1. Create a new Contact in Odoo with Name, Email, and Phone.
    2. Save the record.
- **Expected Result**: 
    - A new entry appears in **Webhook Logs**.
    - Log state is **Success**.
    - Request body contains the correct JSON data.

### Test Case 1.2: Conditional Trigger (Domain Filter)
- **Scenario**: Only trigger webhook when a Sale Order is "Confirmed".
- **Prerequisites**: Webhook configured for `sale.order` with Filter Domain `[('state', '=', 'sale')]`.
- **Steps**:
    1. Create a Quotation and Save.
    2. Confirm the Sale Order.
- **Expected Result**: 
    - No log entry is created during Step 1.
    - A log entry is created immediately after Step 2.

### Test Case 1.3: Custom Payload Adaptation
- **Scenario**: Transform Odoo field names to match external API requirements.
- **Code**: `payload.update({'remote_name': record.name})`
- **Steps**: Trigger the webhook.
- **Expected Result**: The outgoing JSON contains `"remote_name"` instead of `"name"`.

---

## 📥 2. Inbound Webhook Test Cases (External to Odoo)

### Test Case 2.1: JSON Payload Processing
- **Scenario**: Update a Partner's contact details via external POST.
- **Prerequisites**: Inbound route configured for `res.partner`.
- **Action**: Use a tool (like Postman) to POST `{"id": 1, "phone": "999-000"}` to the inbound URL.
- **Expected Result**: 
    - Odoo returns `{"status": "success"}`.
    - Partner record with ID 1 has the new phone number.

### Test Case 2.2: Security Verification (HMAC Signature)
- **Scenario**: Reject requests that do not have a valid security signature.
- **Steps**:
    1. Send request with valid `X-Hub-Signature`. -> **Expected**: Success.
    2. Send request with invalid or missing signature. -> **Expected**: HTTP 200 with `{"status": "error", "message": "Invalid signature"}`.

---

## 🛡️ 3. Authentication & Security Tests

### Test Case 3.1: Basic Authentication
- **Action**: Configure a webhook with a wrong password in the Authentication record.
- **Expected Result**: Webhook Log shows **Error** with status code **401 Unauthorized**.

### Test Case 3.2: Bearer Token
- **Action**: Send an inbound request without the `Authorization: Bearer <token>` header.
- **Expected Result**: Odoo script detects missing header and returns an error message.

---

## ⚠️ 4. Error Handling & Reliability

### Test Case 4.1: Manual Retry (Failover)
- **Scenario**: External server returns a 500 error.
- **Steps**:
    1. Trigger webhook while target server is offline. (Log = **Error**).
    2. Fix target server.
    3. Click **"Resend"** button on the log entry in Odoo.
- **Expected Result**: A new request is sent, and the log updates to **Success**.

### Test Case 4.2: Timeout Handling
- **Action**: Set a low timeout (e.g., 1 second) for a slow external API.
- **Expected Result**: Log shows **Error** with message `Connection Timeout`.

### Test Case 4.3: Malformed JSON
- **Action**: Send a broken JSON string to the inbound route.
- **Expected Result**: Odoo returns an error indicating the JSON is invalid (handled by our controller fix).
