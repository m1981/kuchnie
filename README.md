# 🧠 Synthadoc: Kitchen Company Brain (Mac M2 Guide)

This document contains all the commands needed to install, run, and maintain our AI-powered knowledge base using Synthadoc and Google Gemini.

## 1. First-Time Installation (Using `uv`)

We use `uv` because it is lightning-fast on Mac M2. These steps assume you have your terminal open in your `kuchnie` repository (`~/PycharmProjects/kuchnie`).

```bash
# 1. Install uv (if you don't have it already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the Synthadoc engine to your home folder (outside this repo)
cd ~
git clone https://github.com/paulmchen/synthadoc.git

# 3. Go back to your kitchen repo
cd ~/PycharmProjects/kuchnie

# 4. Create a blazing fast virtual environment using uv
uv venv

# 5. Activate the environment
source .venv/bin/activate

# 6. Install Synthadoc into this environment
uv pip install -e ~/synthadoc

# 7. Verify installation
synthadoc --version
```

---

## 2. 🌅 Daily Start-Up (After a Mac Restart)

When you restart your Mac or open a fresh terminal window, the background server is dead and your API key is forgotten. **Run these 3 commands to wake the AI back up:**

```bash
# 1. Go to your repo and activate the Python environment
cd ~/PycharmProjects/kuchnie
source .venv/bin/activate

# 2. Give it the API key (Replace with your actual key)
export GEMINI_API_KEY="..."

# 3. Start the background engine
synthadoc serve --background
```

_You can now close the terminal or keep working. The AI is running silently in the background._

---

## 3. 📚 The Ingestion Workflow (Feeding the AI)

Do **NOT** ingest the whole repository at once. Feed the AI in this specific order so it builds a clean "tree" of knowledge.

**Phase 1: The Trunk (Core Rules & SOPs)**

```bash
synthadoc ingest --batch 00_Dokumenty_Strategiczne/
synthadoc ingest --batch 07_SOP_Montaz/
synthadoc ingest --batch 08_Szkolenia_Corpus/
```

**Phase 2: The Branches (Visual Cheat Sheets)**

```bash
synthadoc ingest --batch 05_Montaz_i_Sprzet/
synthadoc ingest --batch 03_Materialy_i_Katalogi/Sciagi_i_Wzorniki/
```

**Phase 3: The Leaves (Heavy Catalogs - Takes time)**

```bash
synthadoc ingest --batch 03_Materialy_i_Katalogi/Egger/
synthadoc ingest --batch 03_Materialy_i_Katalogi/Krono/
```

**Phase 4: Specific Business Logic (Do not batch the whole folder)**

```bash
synthadoc ingest 01_Biznes_i_Sprzedaz/Skrypty_Sprzedazowe/ja-vs-ikea.md
synthadoc ingest 01_Biznes_i_Sprzedaz/Marketing_i_Portfolio/00-reklama.md
```

---

## 4. 🔍 Asking Questions (Querying)

You don't have to open Obsidian to ask a question. You can ask the AI directly from your terminal. It will answer based _only_ on your company files.

```bash
# Ask a quick question
synthadoc query "Jaki jest odstęp dylatacyjny dla blatu kompaktowego Egger?"

# Ask a question and save the answer as a permanent page in the wiki
synthadoc query "Podsumuj różnice między HPL a blatem kompaktowym" --save
```

---

## 5. 🛠️ Maintenance & Monitoring

Use these commands to check on the AI and keep the wiki healthy.

**Check what the AI is currently doing:**

```bash
synthadoc jobs list
```

**Retry a job if it failed (e.g., internet disconnected):**

```bash
synthadoc jobs retry <job-id>
```

**Run the Linter (Finds contradictions and broken links):**
_Run this once a week or after a massive catalog upload._

```bash
synthadoc lint run
```

**Rebuild the Table of Contents (`index.md`):**
_Run this after adding a lot of new files so the AI updates the main dashboard._

```bash
synthadoc scaffold
```

---

## 6. 🛑 Git Best Practices

To keep your GitHub/GitLab repository clean, ensure your `.gitignore` file in the `kuchnie` folder contains these exact lines:

```text
# Python virtual environment
.venv/

# Synthadoc hidden database and logs
.synthadoc/
log.md

# (Optional) Ignore raw extracted text cache
.synthadoc/extracted/
```

**What you SHOULD commit to Git:**

- `wiki/` (This contains all the Markdown files the AI generated. Commit this so your knowledge base is backed up!)
- `AGENTS.md` (Your custom AI instructions).
