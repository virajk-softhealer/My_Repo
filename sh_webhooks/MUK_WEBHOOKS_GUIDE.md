# MuK Webhooks: End-to-End Guide & Implementation Reference

This guide provides a comprehensive overview of how the **MuK Webhooks** module works in Odoo 19, covering configuration, workflows, and testing scenarios.

---

## 📖 1. Overview
Webhooks are user-defined HTTP callbacks triggered by specific events. In Odoo, they allow you to push data to external systems (Outbound) or receive data from external sources (Inbound) in real-time.

### Core Components:
- **Webhook Actions**: Defined as Server Actions that execute HTTP requests.
- **Automation Rules**: Link Odoo events (Create/Update/Delete) to Webhook Actions.
- **Authentication**: Centralized management of Basic, Token, or OAuth2 credentials.
- **Webhook Logs**: Complete traceability of every request and response.

---

## ⚙️ 2. End-to-End Workflow (Outbound)

### Step 1: Authentication Configuration
Before creating a hook, define how you will authenticate with the target system.
- Go to **Settings > Webhooks > Authentication**.
- Support for **Basic Auth**, **Digest**, **Bearer Tokens**, and **OAuth2** (Client Credentials/Password).

### Step 2: Create a Webhook Action
- Go to **Settings > Webhooks > Webhooks**.
- Define the **Target URL** and **HTTP Method** (POST, PUT, GET, DELETE).
- **Adapt Payload**: 
    - Select Odoo fields to include in the JSON body.
    - Use the **Python Code** tab to transform data.
    - *Variable `records` contains the records being processed.*
- **Adapt Headers**: Add custom headers (e.g., `X-Source: Odoo`).

### Step 3: Triggering (Automation)
- Create a **Base Automation** rule.
- Select your model (e.g., `Sales Order`).
- Select the **Trigger** (e.g., `On Save`).
- Set the **Action to Do** as the Webhook Action you created in Step 2.

---

## 📥 3. End-to-End Workflow (Inbound)

### Step 1: Define the Route
- Create an **Incoming Webhook Route**.
- The module generates a unique, token-secured URL: `https://your-odoo.com/webhooks/incoming/<token>`

### Step 2: Processing Python Code
Write the logic to handle the incoming data.
- **Available Variables**: `env`, `payload` (JSON body), `headers`, `result` (response body).
- *Example:*
  ```python
  if payload.get('event') == 'payment_success':
      order = env['sale.order'].search([('name', '=', payload.get('order_ref'))])
      order.action_confirm()
      result['status'] = 'confirmed'
  ```

---

## 🧪 4. Test Cases & Scenarios

### Case A: Syncing New Customers to External CRM
- **Model**: `res.partner`
- **Trigger**: `On Creation`
- **Payload Adaptation**:
  ```python
  payload.update({
      'external_id': record.id,
      'full_name': record.name,
      'source': 'Odoo ERP'
  })
  ```
- **Test**: Create a contact in Odoo. Verify the log shows a 201 Created status and the correct JSON body.

### Case B: Handling Response Data (Bi-directional Sync)
- **Scenario**: After sending an Invoice to a 3rd party, save their system's ID back to Odoo.
- **Process Response Code**:
  ```python
  if response.status_code == 200:
      ext_id = response.json().get('remote_id')
      record.write({'x_external_system_id': ext_id})
  ```

### Case C: Failover & Manual Retry
- **Scenario**: The external server was down (HTTP 503).
- **Test**:
    1. Check **Webhook Logs**. The entry will be marked as **Error**.
    2. Click the **"Resend"** button on the log entry once the server is back up.
    3. Verify the state changes to **Success**.

### Case D: Conditional Execution (State Change)
- **Scenario**: Only notify the shipping provider when a Sale Order is confirmed.
- **Model**: `sale.order`
- **Trigger**: `On Update`
- **Filter Domain**: `[('state', '=', 'sale')]`
- **Test**: 
    1. Create a draft Sale Order. Verify **NO** webhook is triggered.
    2. Click "Confirm". Verify the webhook log is generated.

### Case E: Security Verification (Inbound HMAC)
- **Scenario**: Verify that the incoming request is actually from a trusted source (e.g., GitHub).
- **Inbound Code**:
  ```python
  import hmac
  import hashlib

  secret = 'my_shared_secret'
  signature = headers.get('X-Hub-Signature-256')
  
  # Calculate expected signature
  expected = 'sha256=' + hmac.new(secret.encode(), request.httprequest.data, hashlib.sha256).hexdigest()
  
  if not hmac.compare_digest(signature, expected):
      result.update({'status': 'error', 'message': 'Invalid signature'})
  else:
      # Process valid data
      result.update({'status': 'success'})
  ```
- **Test**: Send a request with a wrong signature. Verify Odoo returns an error. Send one with a correct signature. Verify it succeeds.

---

## 📊 5. Monitoring & Debugging

- **Analytics**: Use the Graph view on Webhook Logs to see request volume and failure rates.
- **Preview Button**: Always use the **"Preview"** button in the Webhook configuration to build a sample payload and test the URL connection without triggering a real event.

---

## 🛡️ 6. Security Best Practices
1. **Always use HTTPS** for both inbound and outbound URLs.
2. **Rotate Tokens** periodically for Inbound routes.
3. **Use the Authentication object** instead of hardcoding API keys in the Python code blocks.
4. **Whitelist IPs** if the external service provides a static range for their webhooks.
