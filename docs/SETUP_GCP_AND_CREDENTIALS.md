# Set Up Google Cloud and Local Credentials (AWS-Familiar Guide)

This guide gets you from zero to: (1) a GCP project with the right APIs and a service account, (2) **local credentials** so scripts and the app can call GCP from your machine, and (3) **deployment credentials** so you can deploy Magic Apron to Cloud Run from code. Every GCP concept is related to its **AWS equivalent** so you can map what you already know.

---

## Quick reference: GCP ↔ AWS

| Goal | GCP | AWS equivalent |
|------|-----|-----------------|
| CLI + default credentials | `gcloud` + Application Default Credentials (ADC) | `aws` CLI + default profile / `AWS_ACCESS_KEY_ID` |
| Local “who am I?” auth | `gcloud auth application-default login` | `aws configure` + env vars or `~/.aws/credentials` |
| Server/deploy auth | Service account key (JSON) or workload identity | IAM user access keys or IAM role for EC2/ECS/Lambda |
| Project boundary | GCP **Project** (billing, APIs, resources) | AWS **Account** (or org) |
| Run a container | **Cloud Run** | ECS Fargate, Lambda (container), or App Runner |
| Object storage | **Cloud Storage (GCS)** | S3 |
| Managed RAG/search | **Vertex AI Search** (Discovery Engine) | Kendra + Bedrock Knowledge Bases |

---

## Step 1: Create a Google Cloud account and project

1. **Sign up** (if needed): [console.cloud.google.com](https://console.cloud.google.com). You get a free tier; new users often get trial credits (similar to AWS Free Tier).
2. **Create a project** (like an AWS account or a logical “folder” for billing and APIs):
   - In the top bar: **Select a project** → **New Project**.
   - Name it (e.g. `magic-apron-poc`), choose organization or “No organization”, then **Create**.
3. **Note your Project ID** (e.g. `magic-apron-poc-12345`). You’ll use it as `GOOGLE_CLOUD_PROJECT` everywhere.

4. **Enable billing** on the project (required for Vertex AI, Cloud Run, and most APIs; free tier still applies):
   - Go to [Billing](https://console.cloud.google.com/billing) and **Link a billing account** to your project (or create a billing account first if you don't have one).
   - New users often get **free trial credits**; you won't be charged until you exceed the free tier or credits. Set a budget alert if you want (Billing → Budgets & alerts).

**AWS parallel:** A GCP Project is roughly like an AWS account (or a tagged set of resources in one account). Billing and IAM are scoped to the project. Linking billing is like having a payment method on file for an AWS account; free tier still applies.

---

## Step 2: Install and configure the gcloud CLI

The **gcloud** CLI is the main way to manage GCP from the terminal (like the **aws** CLI for AWS).

1. **Install** (pick one):
   - **SDK in your home directory (recommended if you installed from the website):**  
     The SDK is at `~/google-cloud-sdk` (i.e. `/Users/YOUR_USERNAME/google-cloud-sdk`). Add it to your PATH and run the installer if you haven’t already:
     ```bash
     export PATH="$HOME/google-cloud-sdk/bin:$PATH"
     # One-time setup (prompts for shell config, etc.):
     "$HOME/google-cloud-sdk/install.sh"
     ```
     To make the PATH permanent, add the `export PATH=...` line to `~/.zshrc` (zsh) or `~/.bash_profile` (bash), then open a new terminal or run `source ~/.zshrc`.
   - **macOS (Homebrew):** `brew install --cask google-cloud-sdk` (installs under Homebrew; no need to set PATH).
   - **Official installer:** [Install gcloud](https://cloud.google.com/sdk/docs/install) — choose install location when prompted.
2. **Log in** (interactive browser login, like `aws configure` but with OAuth):
   ```bash
   gcloud auth login
   ```
3. **Set default project** (so you don’t pass `--project` every time):
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```
   You may see a message that the project *lacks an 'environment' tag*. That’s optional governance (like AWS tags on an account/resource). The project is still set correctly; you can continue. To add the tag (e.g. for policy or to clear the message), you need a Resource Manager tag value (often created at org level), then:
   ```bash
   # Replace TAG_VALUE_ID with your tag value (e.g. from Console → IAM & Admin → Tags)
   # Parent is your project’s resource name (use your numeric project ID if needed)
   gcloud resource-manager tags bindings create \
     --tag-value=TAG_VALUE_ID \
     --parent=//cloudresourcemanager.googleapis.com/projects/YOUR_PROJECT_ID
   ```
   For a POC you can use value `Development` or `Test` if your org has that tag. Personal accounts without an org can ignore the message.

**AWS parallel:** `gcloud auth login` is like logging in to the AWS SSO or console; `gcloud config set project` is like setting `AWS_PROFILE` or default region.

---

## Step 3: Local credentials (Application Default Credentials, ADC)

Your Python scripts and FastAPI app need to **authenticate** when they call GCP APIs (e.g. Cloud Storage, Vertex AI Search). GCP uses **Application Default Credentials (ADC)**:

- **On your laptop:** ADC is usually the credentials from `gcloud auth application-default login` (stored under `~/.config/gcloud/`).
- **On GCP (e.g. Cloud Run):** ADC is automatically the service account of the running service (no keys needed).

**Do this once on your machine:**

```bash
gcloud auth application-default login
```

A browser window opens; sign in with the same Google account you use for GCP. After that, **all Google client libraries** (e.g. `google-cloud-storage`, `google-cloud-discoveryengine`) will use these credentials when you run code locally.

**AWS parallel:** ADC is like the default credential chain in the AWS SDK (environment variables → `~/.aws/credentials` → IAM role). Here, “default” is your user account via OAuth.

**Verify:**

```bash
# Optional: print current ADC (shows your user and project)
gcloud auth application-default print-access-token
```

If that returns a token, ADC is set. Set the project for ADC too (some libraries use it):

```bash
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
# Or add to your shell profile; also used by our app.
```

---

## Step 4: Enable required APIs

GCP APIs are off by default (like enabling a service in AWS). Enable the ones Magic Apron needs:

```bash
gcloud services enable \
  storage.googleapis.com \
  discoveryengine.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com
```

- **storage.googleapis.com** — Cloud Storage (GCS). *AWS: S3.*  
- **discoveryengine.googleapis.com** — Vertex AI Search (Discovery Engine). *AWS: Kendra / Bedrock.*  
- **run.googleapis.com** — Cloud Run. *AWS: Fargate / Lambda.*  
- **artifactregistry.googleapis.com** — Container registry for Cloud Run. *AWS: ECR.*

---

## Step 5: Service account for deployment (and optional local use)

For **deploying** from your machine (e.g. `gcloud run deploy` or a CI job), you can keep using your user credentials. For **automation or CI**, use a **service account** (like an IAM user or role in AWS).

**Create a service account:**

```bash
export PROJECT_ID=YOUR_PROJECT_ID
export SA_NAME=magic-apron-deploy
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SA_NAME \
  --display-name="Magic Apron deploy and run"
```

**Grant it the roles Cloud Run and GCS need:**

```bash
# So it can deploy and act as the runtime identity for Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

# So it can push images to Artifact Registry
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# So the Cloud Run service can call Vertex AI Search and read GCS if needed
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"
```

**Optional: download a key for local or CI use (like an AWS access key):**

```bash
mkdir -p .keys
gcloud iam service-accounts keys create .keys/magic-apron-deploy.json \
  --iam-account=$SA_EMAIL
```

**Use the key only when needed** (e.g. CI, or a second terminal that shouldn’t use your user ADC):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=".keys/magic-apron-deploy.json"
```

**Important:** Add `.keys/` to `.gitignore` so the key is never committed. For day-to-day local dev, `gcloud auth application-default login` is enough; you don’t need a key file.

**AWS parallel:** Service account ≈ IAM user; the JSON key ≈ access key + secret. IAM policy bindings ≈ attaching policies to that user/role.

---

## Step 6: Environment variables for Magic Apron

Your app and scripts need to know **project** and **data store**:

```bash
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export MAGIC_APRON_DATA_STORE_ID=your_data_store_id   # From Vertex AI Search console
export VERTEX_LOCATION=global   # Or the region where you created the data store
```

**Where to get `MAGIC_APRON_DATA_STORE_ID`:**  
In Cloud Console → **Vertex AI** → **Search and conversation** → your app → Data Store. The ID is in the URL or the data store details. You create the data store and point it at your GCS bucket (see CONCEPTS_AND_ARCHITECTURE.md and the 3-day roadmap).

**Optional:** Put these in a `.env` file and load with `python-dotenv` (or export in your shell profile). Do **not** commit `.env` if it ever contains secrets.

---

## Step 7: Deploy via code (Cloud Run)

Once ADC (or a service account key) is set and APIs are enabled:

1. **Build and push the image** (see `scripts/deploy.sh` or the commands in README).
2. **Deploy the service:**
   ```bash
   ./scripts/deploy.sh
   # Or: gcloud run deploy magic-apron --source . --region us-central1 --allow-unauthenticated
   ```

Cloud Run will use the **default compute service account** of the project unless you override it. That account needs `roles/aiplatform.user` (and optionally `roles/storage.objectViewer`) so the running container can call Vertex AI Search (and GCS if you add that later).

**Grant the default compute SA access to Vertex AI:**

```bash
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/aiplatform.user"
```

**AWS parallel:** Cloud Run’s “default service account” is like the ECS task execution role / task role: the identity under which your container runs. Giving it `aiplatform.user` is like giving an ECS task role permission to call Bedrock/Kendra.

---

## Summary checklist

- [ ] GCP account and project created; Project ID noted.  
- [ ] `gcloud` installed; `gcloud auth login` and `gcloud config set project` done.  
- [ ] `gcloud auth application-default login` done (local ADC).  
- [ ] Required APIs enabled (Storage, Discovery Engine, Run, Artifact Registry).  
- [ ] (Optional) Service account created and key in `.keys/`; `.keys/` in `.gitignore`.  
- [ ] `GOOGLE_CLOUD_PROJECT` and `MAGIC_APRON_DATA_STORE_ID` set (and optionally `GOOGLE_APPLICATION_CREDENTIALS` if using a key).  
- [ ] Default compute service account granted `roles/aiplatform.user` for Cloud Run.  
- [ ] Run `python scripts/generate_mock_data.py`, upload to GCS, create Vertex AI Search data store, then run or deploy the app.

After this, you can run the FastAPI app locally and deploy to Cloud Run from your machine or CI using the same credentials model you’re used to on AWS.
