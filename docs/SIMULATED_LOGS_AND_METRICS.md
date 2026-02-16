# Simulated Logs and Metrics — What to Look For in GCP

When you practice the **MONITORING_SCENARIOS.md** situations, use these examples to imagine what you’d see in **Cloud Logging** and **Cloud Monitoring**. They help you explain in an interview: “I’d look for X in the logs and Y in the metrics.”

---

## 1. Application logs (FastAPI / Magic Apron API)

If your FastAPI app writes structured logs (e.g. JSON with `request_id`, `latency_ms`, `status`), they might look like this in **Logs Explorer**.

**Successful request:**
```json
{
  "severity": "INFO",
  "message": "search request completed",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "query": "What do I need to fix a leaky faucet?",
  "latency_ms": 847,
  "status": "ok",
  "results_count": 5
}
```

**Failed request (e.g. Search API error):**
```json
{
  "severity": "ERROR",
  "message": "search request failed",
  "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "query": "Where are plungers?",
  "error": "503 Service Unavailable",
  "detail": "Vertex AI Search backend temporarily unavailable"
}
```

**What you’d do in Logs Explorer:**  
Filter by `resource.type="cloud_run_revision"` (or your FastAPI resource), `severity>=ERROR`, and time range. Search for `request_id` or `error` to trace a specific failure.

---

## 2. Simulated “high latency” metric (Scenario 1)

In **Metrics Explorer**, you might create a chart for:

- **Metric:** e.g. `api/request_latency` or Discovery Engine equivalent (exact name depends on the product; could be under “Consumed API” or “Vertex AI Search”).
- **Group by:** `method` or `data_store_id`.
- **Alignment:** 95th percentile, 1-minute period.

**Simulated view:**  
You see a spike where p95 goes from ~500 ms to 2.5 s for a 10-minute window. That’s the “alert” condition: you’d correlate with request count and quota usage as in MONITORING_SCENARIOS.md.

---

## 3. Simulated “spike in 5xx” (Scenario 2)

**Error Reporting** might show:

- **Error type:** `500 Internal Server Error`
- **Count:** 50 in the last hour (vs 0–2 normally).
- **First seen:** 14:32 UTC.

**Logs Explorer** for one of those errors:

```text
Traceback (most recent call last):
  ...
  File "app/main.py", line 45, in search
    out = search_magic_apron(req.query)
  ... discoveryengine.exceptions.ServiceUnavailable: 503 Backend error
```

That tells you the failure is **downstream** (Vertex AI Search), not a bug in your app logic. You’d then check Vertex AI status and quotas.

---

## 4. Simulated “cost spike” (Scenario 3)

In **Billing → Reports**, after filtering by “Vertex AI” (or “Discovery Engine”):

- **Last month:** $200.
- **This month (current):** $320 and climbing.

You’d break down by **SKU** (e.g. “Vertex AI Search queries”, “Gemini predictions”) and by **day** to see when the increase started. That supports the “compare Flash vs Pro” and “who is calling the API” discussion in MONITORING_SCENARIOS.md.

---

## 5. Adding these to your app (optional)

To make monitoring real instead of simulated:

1. **Structured logging:** In FastAPI, log a JSON line per request with `request_id`, `latency_ms`, `status`, and optionally `query` (redact if needed).
2. **Custom metric:** Use the Cloud Monitoring client to write a custom metric `magic_apron/search_latency` so you can alert on p95 in your project.
3. **Cloud Trace:** Instrument the outgoing call to Vertex AI Search so each request has a span; then you see “time in Search” vs “time in app” in the Trace UI.

Use this file together with **MONITORING_SCENARIOS.md** to practice: “If I see this log or this metric, I would do X next.”
