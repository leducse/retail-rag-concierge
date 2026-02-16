# Simulated Monitoring Situations — Magic Apron on GCP

Use these scenarios to practice **how you’d respond** using **Cloud Monitoring** and **Cloud Logging**. In an interview, you can say: “Here’s how I’d detect and debug this on Google Cloud.”

**If you’re used to AWS:** Every GCP tool below has an AWS counterpart. Use the table to map the mental model.

---

## GCP monitoring basics (and AWS equivalents)

| GCP tool | Purpose | AWS equivalent |
|----------|---------|----------------|
| **Cloud Monitoring** (formerly Stackdriver) | Metrics, dashboards, alerting policies, SLOs. | **CloudWatch** (metrics, dashboards, alarms). |
| **Cloud Logging** | Logs from GCP services and your app (FastAPI). | **CloudWatch Logs** (log groups, streams, Insights). |
| **Error Reporting** | Aggregates errors from logs (e.g. 5xx, exceptions). | **CloudWatch Logs Insights** or X-Ray errors; no exact 1:1. |

**Where to go in Console:**  
- **Monitoring** → Dashboards, Alerting, Metrics Explorer. *(AWS: CloudWatch → Dashboards, Alarms, Metrics.)*  
- **Logging** → Logs Explorer (query by resource, severity, text). *(AWS: CloudWatch → Log groups → Logs Insights.)*  
- **Vertex AI** → Your project → Monitor usage and quotas. *(AWS: Bedrock / Kendra console usage.)*

---

## Scenario 1: “Search API latency is high”

**Simulated situation:**  
An alert fires: *p95 latency for Vertex AI Search requests &gt; 2 seconds* (or your chosen threshold).

### What to do (step by step)

1. **Open Cloud Monitoring**
   - Go to **Monitoring → Alerting** and find the firing policy.
   - Click the alert and open the **Metrics Explorer** or the dashboard that shows Search API latency.

2. **Confirm the metric**
   - In Metrics Explorer, select:
     - **Resource type:** e.g. “Discovery Engine” / “Vertex AI Search” (or “Consumed API” if that’s how it’s exposed).
     - **Metric:** request latency (e.g. `request_latency` or `rpc_client_latency`).
   - Break down by **method** or **data_store_id** to see if one data store or endpoint is slow.

3. **Check for throttling or quota**
   - **IAM & Admin → Quotas** for Vertex AI Search / Discovery Engine: see if you’re near quota (could cause queuing and higher latency).
   - **Vertex AI → Dashboard**: check for quota or limit messages.

4. **Correlate with load**
   - Add a metric for **request count** on the same time range. If latency went up when traffic spiked, it could be:
     - Normal load-related latency.
     - Need for more quota or different capacity (if applicable).

5. **Interview answer**
   - “I’d open the alert in Cloud Monitoring, inspect the latency metric in Metrics Explorer, and break down by API method or data store. I’d check Vertex AI quotas and request volume to see if we’re hitting limits or if it’s a backend issue. If it’s our FastAPI app calling Search, I’d also check our app’s logs and any custom latency metrics we emit.”

---

## Scenario 2: “Spike in 5xx errors from our API”

**Simulated situation:**  
Users report errors. Error Reporting or an alert shows a spike in 5xx (or uncaught exceptions) from the Magic Apron API.

### What to do

1. **Error Reporting**
   - **Monitoring → Error Reporting** (or **Logging → Error Reporting**).
   - See which service and which error type spiked (e.g. “500 Internal Server Error”, “Connection timeout”).

2. **Logs Explorer**
   - **Logging → Logs Explorer**.
   - Filter by:
     - **Resource:** the Cloud Run service (or VM) running FastAPI.
     - **Severity:** Error (or “default” and search for “error” / “exception”).
     - **Time range:** the spike window.
   - Search for the exact error message or trace ID.

3. **Trace**
   - If you use **Cloud Trace**, open the trace for a failing request to see which step failed (e.g. call to Vertex AI Search, timeout, or auth).

4. **Downstream dependency**
   - If errors are “timeout” or “503” when calling Vertex AI Search, check:
     - **Vertex AI** status page and quotas.
     - Your **Search** data store status (e.g. re-indexing or outage).

5. **Interview answer**
   - “I’d start with Error Reporting to see the error type, then use Logs Explorer filtered by resource and severity to get request IDs and stack traces. I’d correlate with Cloud Trace if we have it, and check Vertex AI Search availability and our own timeouts and retries.”

---

## Scenario 3: “Budget / cost alert”

**Simulated situation:**  
A budget alert fires: *Vertex AI (or Discovery Engine) cost this month is 150% of last month.*

### What to do

1. **Billing**
   - **Billing → Reports**: filter by **SKU** or **Product** (e.g. “Vertex AI”, “Discovery Engine”, “Gemini”).
   - Break down by **project** and **day** to find when the increase started.

2. **Vertex AI usage**
   - **Vertex AI → Usage** (or the relevant console section) to see:
     - Number of Search requests.
     - Number of Gemini prediction requests (if you call the model directly).
   - Compare to last month or to a baseline (e.g. “we doubled traffic” vs “we switched from Flash to Pro”).

3. **Quotas and usage**
   - Check if a new integration or a runaway client is sending excessive requests (logs + metrics for request count per client or endpoint).

4. **Interview answer**
   - “I’d open the budget alert and then Billing Reports to see which product and SKU increased. For Vertex AI, I’d look at usage metrics—Search API calls and Gemini calls—and correlate with traffic or config changes like switching from Flash to Pro. If it’s unexpected, I’d use logs to find high-volume callers and add rate limiting or caps.”

---

## Scenario 4: “Search returns no or wrong results after a data update”

**Simulated situation:**  
You uploaded new `product_catalog.csv` to GCS, but the chatbot still returns old or no results for new products.

### What to do

1. **Ingestion status**
   - In **Vertex AI Search** (or Discovery Engine) console, open your **Data Store** and check **ingestion** / **indexing** status.
   - Confirm that the last run picked up the new GCS objects and completed without errors.

2. **GCS and indexing**
   - **Storage**: confirm the new file is in the bucket and that the path matches what the data store is configured to read.
   - If the data store uses a **prefix**, ensure the new file is under that prefix.

3. **Index delay**
   - Ingestion can take minutes to hours. Check “last successful ingestion” time; if it’s before your upload, trigger a re-ingestion or wait for the next scheduled run.

4. **Interview answer**
   - “I’d first check the Vertex AI Search data store’s ingestion status and last successful run. I’d confirm the new file is in the right GCS path and that the connector is pointing at that path. If ingestion hasn’t run since the upload, I’d trigger a re-ingestion and then re-test.”

---

## Scenario 5: “Our FastAPI app is slow; we’re not sure if it’s us or Vertex”

**Simulated situation:**  
End-to-end latency for “ask Magic Apron” is high. You need to see whether the time is spent in your app or in the Search API.

### What to do

1. **Add custom metrics**
   - In FastAPI, log or export:
     - **Time to call Search API** (e.g. from request start to Search response).
     - **Time to format response** (after Search returns).
   - Use **OpenCensus** or **Cloud Monitoring client** to write custom metrics (e.g. `magic_apron/search_latency`, `magic_apron/total_latency`).

2. **Cloud Trace**
   - If you use Trace, ensure the FastAPI service creates spans for the outgoing Search call. Then you’ll see in Trace how much time is in “Search” vs “app”.

3. **Logs**
   - Log timestamps at entry and exit of the Search call (e.g. “search_start”, “search_end”). In Logs Explorer, compute duration or use a log-based metric.

4. **Vertex AI metrics**
   - In Monitoring, check Vertex AI / Discovery Engine latency for the same time window. If Search latency is low but total latency is high, the bottleneck is in your app or network.

5. **Interview answer**
   - “I’d add timing around the Vertex AI Search call in our FastAPI app and export those as custom metrics or spans. With Cloud Trace we’d see Search vs app time. I’d also look at Vertex AI’s own latency metrics. That tells us whether to optimize our code or escalate to the Search team.”

---

## Quick reference: where things live in GCP

| What you need | Where |
|---------------|--------|
| API latency, request count | Monitoring → Metrics Explorer (Vertex AI / Discovery Engine or Consumed API) |
| Our app errors | Logging → Logs Explorer (resource = Cloud Run/VM); Error Reporting |
| Cost spike | Billing → Reports; Vertex AI usage |
| Search index freshness | Vertex AI Search → Data Store → Ingestion |
| End-to-end breakdown | Cloud Trace (if instrumented); custom metrics from FastAPI |

Use these scenarios as a script: “When X happens, I go to Y in the console and do Z.” That’s the kind of answer that shows you know GCP monitoring in practice.
