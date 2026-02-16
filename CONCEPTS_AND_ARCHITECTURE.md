# Magic Apron: GCP Concepts and Architecture Decisions

This doc teaches **why** we use each Google Cloud component and how it maps to what you may know from AWS. Use it for interview prep when explaining architecture.

---

## 1. High-level architecture (what we built)

Magic Apron supports **two RAG backends**; we use the **RAG Engine (ragCorpora)** path by default.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────────┐
│  Mock data      │     │  Cloud Storage   │     │  Vertex AI RAG Engine            │
│  (CSV + MD)     │ ──► │  (GCS bucket)    │ ──► │  (RAG corpus / ragCorpora)        │
└─────────────────┘     └──────────────────┘     └────────────┬────────────────────┘
        │                            │                          │
        │  (teaching only)            │                          │  retrieve + ground
        ▼                            │                          ▼
┌─────────────────┐                  │             ┌─────────────────────────────────┐
│  BigQuery       │  (production:     │             │  FastAPI app (Cloud Run or local)│
│  (catalog DB)   │   export to GCS)  │             │  • Serves static frontend (/)   │
└─────────────────┘                  │             │  • POST /search → RAG query      │
                                     │             └────────────┬────────────────────┘
                                     │                          │
                                     │                          │  Tool.from_retrieval
                                     │                          ▼
                                     │             ┌─────────────────────────────────┐
                                     │             │  Gemini 2.0 Flash                │
                                     │             │  • Grounded answer + citations   │
                                     │             └─────────────────────────────────┘
```

**Data flow (RAG Engine path):**

1. **Ingestion:** CSV and markdown files are uploaded to a **GCS** bucket. A **RAG corpus** (ragCorpora) is created in the Vertex AI console and configured to ingest from that GCS path. Google chunks and embeds the content.
2. **Query:** The user asks a question in the frontend. The FastAPI app calls the Vertex AI RAG API with the corpus resource name. We use **Gemini 2.0 Flash** with **Tool.from_retrieval** so the model retrieves from the corpus and generates an answer grounded on those chunks.
3. **Response:** The app returns the answer text plus **citations** (title, snippet, URI) serialized from the API’s grounding metadata. The frontend renders them in a readable “Sources” section.

**Alternative path (Discovery Engine):** The same app can use **Vertex AI Search** (Discovery Engine) with a **data store** instead of a RAG corpus. Set `MAGIC_APRON_DATA_STORE_ID` and `VERTEX_LOCATION`; the code uses the Search API and returns summary + citations in a similar shape. AWS analogue: Kendra + Bedrock Knowledge Bases.

---

## 2. Component-by-component (concepts + decisions)

### 2.1 Cloud Storage (GCS) — “Where the raw data lives”

**What it is:** Object storage in GCP. Same idea as **Amazon S3**: buckets, objects, versioning, lifecycle rules.

**Why we use it here:**  
Vertex AI Search can **ingest from GCS**. So we put the product catalog CSV and DIY markdown files in a bucket and point the Search data store at that bucket. No need to run our own servers to “serve” the files.

**Architecture decision:**  
We could have put data in BigQuery only; but Search’s out-of-the-box connector is often “GCS (or website)”. For mixed content (CSV + markdown), a single bucket is simple. In production, a scheduled job would write **from BigQuery (or a data lake) to GCS**, and Search would re-index on a schedule or trigger.

---

### 2.2 RAG Engine (ragCorpora) and Vertex AI Search (Discovery Engine)

**What we use in this POC:** **Vertex AI RAG Engine** with a **RAG corpus** (ragCorpora). The corpus is created in the console, pointed at a GCS path, and ingested. The app uses the Vertex AI Python SDK (`vertexai.rag`, `GenerativeModel` with `Tool.from_retrieval`) so Gemini retrieves from the corpus and returns a grounded answer with citations. *AWS analogue:* Bedrock Knowledge Bases + retrieve + invoke model with retrieved context.

**Alternative:** **Vertex AI Search** (Discovery Engine) uses a **data store** and **serving config**; one Search API call returns retrieval + optional summarization. *AWS analogue:* Kendra + Bedrock Knowledge Bases in one flow.

**Why RAG Engine here:** One corpus for catalog + DIY; no vector DB or embedding pipeline to run; Gemini Flash with retrieval tool gives low latency and clear citations (URI, title, text snippet).

**Architecture decision:** The app supports **both** backends via env: `MAGIC_APRON_RAG_CORPUS` (RAG Engine) or `MAGIC_APRON_DATA_STORE_ID` (Discovery Engine). We use the RAG Engine path by default.

---

### 2.3 RAG corpus / data store and ingestion

**Concept:**  
- **RAG Engine:** A **RAG corpus** (ragCorpora) is the container. You create it in the console, set the source (e.g. GCS URI), and run **ingestion**. Google chunks and embeds the content; then queries hit this index via the RAG API.  
- **Discovery Engine:** A **data store** is the container; you point it at GCS (or website, BigQuery) and run ingestion. Queries use the Search API.

**Why GCS first:**  
Both paths ingest from **GCS** (or other connectors). Day 1: upload CSV and markdown to a bucket. Day 2: create the RAG corpus (or data store), set the source path (e.g. `gs://bucket/magic_apron/`), and run ingestion. Later, re-ingest on a schedule or when content changes. *AWS:* Same idea as syncing S3 to a Kendra index or Bedrock Knowledge Base.

---

### 2.4 BigQuery (and how it would feed this in production)

**What it is:** GCP’s data warehouse. Analogous to **Amazon Redshift** (and to some extent Athena). Tables, SQL, streaming inserts, exports to GCS.

**In this POC:**  
We don’t use BigQuery in the code; we generate a local CSV and upload it to GCS. So BigQuery is **teaching only** here.

**In production at a retailer:**  
- Product catalog typically lives in a **warehouse** (e.g. BigQuery tables).  
- ETL or scheduled jobs **export** catalog (and maybe content) to GCS (e.g. daily CSV/JSON export).  
- Vertex AI Search **ingests from that GCS path**. So the flow is: **BigQuery → export to GCS → Vertex AI Search indexes GCS.**  
- Same idea for “DIY guides” if they’re in a CMS or DB: export to GCS (or use a connector if Search supports it), then index.

**Architecture decision:**  
We keep the POC simple: files in GCS only. For the interview, you can say: “In production, catalog would come from BigQuery via scheduled exports to GCS, and Search would ingest from GCS.”

---

### 2.5 Gemini (Flash vs Pro) — “Who generates the summary?”

**What it is:** Google’s LLM family on Vertex AI. **Gemini 1.5 Flash** is faster and cheaper; **Gemini 1.5 Pro** is more capable and more expensive.

**Where it appears:**  
When you use Vertex AI Search’s “search + summarize” (grounded search), the **summary** is generated by a model. That can be configured to use Flash or Pro (or others). Your FastAPI app may also call Gemini directly if you do custom summarization on top of Search results.

**Architecture decision (interview talk track):**  
- **Magic Apron (conversational Q&A):** Prefer **Flash** for latency and cost; users expect quick answers.  
- **Blueprint takeoff / complex analysis:** Prefer **Pro** for harder reasoning and accuracy; latency is less critical.  
See `MONITORING_SCENARIOS.md` and the “Day 3” comparison doc for cost/latency.

---

### 2.6 FastAPI backend and frontend

**What we do:**  
- **Backend:** FastAPI app that loads config from **.env** (`GOOGLE_CLOUD_PROJECT`, `MAGIC_APRON_RAG_CORPUS` or `MAGIC_APRON_DATA_STORE_ID`). It receives a question at `POST /search`, calls the RAG Engine (or Discovery Engine) API, serializes citations to JSON-safe dicts (protobuf `RetrievedContext` → uri/title/text), and returns `summary_text`, `citations`, `results_count`, and `latency_ms`.  
- **Frontend:** A single static page (`static/index.html`) served at `/`. The user types a question, clicks “Ask Magic Apron”; the page calls `/search` and displays the answer plus a formatted **Sources** section (title, snippet, GCS URI per citation).

**Why FastAPI:**  
Simple, async-friendly, easy to add auth and rate limiting. We run on **Cloud Run** (AWS: Fargate, Lambda container, or App Runner). Global exception handling returns JSON errors so the frontend never parses HTML.

**Architecture decision:**  
One code path for RAG Engine and one for Discovery Engine; env vars choose the backend. Citations are normalized so the frontend always gets `{ uri, title, text?, document_name? }` for display.

---

## 3. Summary: GCP ↔ AWS mapping (for interviews)

| We use (GCP)              | Rough AWS equivalent              | Role in Magic Apron                    |
|---------------------------|-----------------------------------|----------------------------------------|
| Cloud Storage (GCS)       | S3                                | Store CSV + DIY markdown; source for RAG |
| RAG Engine (ragCorpora)   | Bedrock Knowledge Bases + retrieve | Corpus, retrieval, Gemini grounding    |
| Vertex AI Search (optional) | Kendra + Bedrock KB              | Alternative: data store + Search API   |
| Vertex AI (Gemini)        | Bedrock (e.g. Claude)             | Grounded answer (Flash)                |
| BigQuery                  | Redshift                          | Production source of catalog (teaching) |
| Cloud Run                 | Fargate / Lambda container        | Host FastAPI + static frontend         |
| Cloud Monitoring/Logging  | CloudWatch                       | Metrics, logs, alerts                  |

---

## 4. What to say in an interview

- **“Why Vertex AI Search and not build our own vector DB?”**  
  “We wanted a managed RAG experience: indexing, retrieval, and grounded summarization with citations. Vertex AI Search gives us that without operating embeddings or vector infra. For a POC and for a first production slice, that’s the right tradeoff.”

- **“How would production data get into the system?”**  
  “Catalog data lives in BigQuery. We’d run a scheduled job to export to GCS. Vertex AI Search would ingest from that GCS path. DIY content could be exported from a CMS to GCP the same way, or we’d use a connector if available.”

- **“Why Gemini Flash for Magic Apron?”**  
  “Conversational Q&A needs low latency and high throughput. Flash is cheaper and faster; for this use case the quality is sufficient. We’d use Pro for more complex tasks like blueprint takeoff where reasoning matters more than sub-second response.”

---

## 5. How we would improve the app

These are concrete next steps for production or a stronger portfolio demo. Use them in interviews to show you think beyond the POC.

**Data and ingestion**

- **Live catalog:** Replace mock CSV with a scheduled job that exports from **BigQuery** (or a product API) to GCS so the RAG corpus stays in sync. Add **Eventarc** or Cloud Scheduler to trigger re-ingestion when new files land in the bucket.
- **More content:** Ingest more DIY guides, store policies, or store locator data into the same or separate corpora and tune chunking/embedding for each type.
- **Metadata and filters:** Use RAG retrieval filters (e.g. by category or region) so answers can be scoped to relevant products or stores.

**API and backend**

- **Auth and rate limiting:** Add **Firebase Auth** or **Cloud Identity** (or API keys) so only authorized users or apps can call `/search`. Add rate limits per user or API key to avoid abuse and control cost.
- **Caching:** Cache responses for frequent or repeated queries (e.g. in **Memorystore for Redis** or a short-lived in-process cache) to reduce latency and Vertex AI cost.
- **Structured logging and tracing:** Emit **Cloud Logging** structured logs (request_id, latency_ms, corpus_id, token counts) and use **Cloud Trace** for the RAG + Gemini call so we can debug and monitor per request.
- **Fallback and safety:** If RAG returns no or low-confidence results, return a clear “I couldn’t find that” message instead of letting the model guess. Add optional content filters or guardrails for sensitive topics.

**Frontend and UX**

- **Conversation history:** Keep a short conversation context (e.g. last N turns) and pass it to the model so follow-up questions (“Where is that?” “What about the price?”) work without repeating context.
- **Streaming:** Use **streaming** from the Gemini API so the answer appears incrementally instead of waiting for the full response.
- **Mobile and a11y:** Improve responsive layout and keyboard/screen-reader support so the app works well on phones and for accessibility.
- **Feedback:** Add thumbs up/down or “Was this helpful?” and log feedback (e.g. to BigQuery or Firestore) to measure quality and tune retrieval/prompts.

**Cost and operations**

- **Budget and alerts:** Set a **GCP budget** and alerts so we’re notified before spend exceeds a threshold. Optionally cap daily or per-user RAG/Gemini usage.
- **Model choice:** A/B test **Gemini Flash vs Pro** (or different sizes) for this workload and lock in based on latency, cost, and quality metrics.
- **Multi-region and HA:** For production, run the app in multiple regions (e.g. Cloud Run in us-central1 and us-east1) and put a load balancer in front for availability and latency.

Next: **MONITORING_SCENARIOS.md** for simulated alerts and how to respond using GCP tools.
