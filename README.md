# 🧠 Synthadoc: Kitchen Company Brain (Mac M2 Guide)

This document contains the streamlined workflow for our AI-powered knowledge base using Synthadoc, Google Gemini, and our custom automation scripts.

## 1. First-Time Setup

We use `uv` to install Synthadoc globally so it is available everywhere without needing virtual environments.

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the engine to your home folder
cd ~
git clone https://github.com/paulmchen/synthadoc.git

# 3. Go to this kitchen repo and install globally
cd ~/PycharmProjects/kuchnie
make install

# 4. Create your secret API key file
echo "GEMINI_API_KEY=..." > .env
```

---

## 2. 🌅 Daily Workflow (The "Make" System)

You no longer need to memorize long commands or activate environments. Everything is handled by the `Makefile`.

**1. Start the AI Engine (Run this once after restarting your Mac):**

```bash
make up
```

_(This automatically loads your API key from `.env` and starts the server in the background)._

**2. Sync New Files (The Smart Way):**
When you add new SOPs or cheat sheets, just run:

```bash
make sync
```

_(This runs our custom `sync.sh` script. It automatically finds new files, skips private client folders, and filters out massive PDFs over 100KB to save tokens)._

**3. Check Progress:**

```bash
make status
```

**4. Weekly Maintenance:**

```bash
make maintain
```

_(This tells the AI to check its own work for contradictions and rebuild the Table of Contents)._

---

## 3. 🛡️ Safety & Exclusions

Our repository contains code (`kitchen-app/`) and private client data (`06_Realizacje/`). We protect it using two layers:

1. **The Script Layer (`sync.sh`):** Automatically ignores `04_Podwykonawcy_CRM`, `06_Realizacje`, and any PDF larger than 100KB. (Run `make sync-dry` to see what it plans to ingest without actually doing it).
2. **The AI Layer (`wiki/purpose.md`):** If a bad file slips through, the AI reads the `STRICT EXCLUSIONS` section at the bottom of `purpose.md` and immediately rejects it.

---

## 4. 🔍 Asking Questions (Querying)

You can ask the AI directly from your terminal. It will answer based _only_ on your company files.

```bash
# Ask a quick question
synthadoc query "Jaki jest odstęp dylatacyjny dla blatu kompaktowego Egger?"

# Ask a question and save the answer as a permanent page in the wiki
synthadoc query "Podsumuj różnice między HPL a blatem kompaktowym" --save
```

---

## 5. 🛑 Git Best Practices

To keep your GitHub/GitLab repository clean, ensure your `.gitignore` file contains these exact lines:

```text
# Secrets
.env

# Synthadoc hidden database and logs
.synthadoc/
log.md

# Sync script artifacts
to_ingest_big.txt
dry_run_manifest.txt
```

**What you SHOULD commit to Git:**

- `wiki/` (This contains all the Markdown files the AI generated. Commit this so your knowledge base is backed up!)
- `AGENTS.md` (Your custom AI instructions).
- `sync.sh` and `Makefile` (Our automation tools).
