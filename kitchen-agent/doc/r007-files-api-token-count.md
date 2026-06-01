# USER

Does the Gemini Python SDK support it attaching PDF?

Yes, absolutely — full support. Here's the complete picture straight from the latest docs (updated May 2026):

---

## Python SDK (`google-genai`) — PDF Support

The current SDK package is **`google-genai`** (not the older `google-generativeai`). Install it with:

```bash
pip install google-genai
```

There are **two methods** depending on your document size.

---

### Method 1 — Inline (small PDFs, < 20 MB)

Pass PDF data inline directly in `generate_content`. This is best suited for smaller documents or temporary processing where you don't need to reference the file in subsequent requests.

```python
from google import genai
from google.genai import types
import httpx

client = genai.Client()

doc_data = httpx.get("https://arxiv.org/pdf/2312.11805").content

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[
        types.Part.from_bytes(
            data=doc_data,
            mime_type='application/pdf',
        ),
        "Summarize this document"
    ]
)
print(response.text)
```

---

### Method 2 — Files API (large PDFs, recommended for multi-turn)

The Files API is recommended for larger documents that you need to refer to in multi-turn interactions, to improve request latency and reduce bandwidth usage.

```python
from google import genai
import io, httpx

client = genai.Client()

pdf_bytes = io.BytesIO(httpx.get("https://arxiv.org/pdf/2312.11805").content)

uploaded = client.files.upload(
    file=pdf_bytes,
    config=dict(mime_type='application/pdf')
)

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[uploaded, "What are the key findings?"]
)
print(response.text)
```

You can also use the newer **Interactions API** (currently beta):

```python
# Interactions API style (beta)
interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input=[
        {"type": "document", "uri": uploaded.uri, "mime_type": uploaded.mime_type},
        {"type": "text", "text": "Summarize this document"}
    ]
)
print(interaction.output_text)
```

---

### Key Limits to Know

The Files API lets you store up to 20 GB of files per project, with a per-file maximum of 2 GB. Files are automatically deleted after 48 hours. The PDF-specific processing cap (for the vision pipeline) is 1,000 pages / 50 MB per document.

---

### Resolution Control (Gemini 3+)

Gemini 3 introduces the `media_resolution` parameter, letting you set resolution to `low`, `medium`, or `high` per individual media part. Very useful for cost control on bulk document pipelines — for dense diagrams use `high`, for mostly-text PDFs `low` is fine.

---

### One Gotcha Worth Noting

You can pass other MIME types like TXT, Markdown, HTML, or XML, but document vision only meaningfully understands PDFs. Other types will be extracted as pure text, and the model won't interpret what's visually rendered — charts, diagrams, and formatting will be lost. So always use `mime_type='application/pdf'` and not a text type, even if your PDF has a lot of text content.

# USER

How does the Anthropi SDK do this? What are the actual costs for 1MB PDF with images for sonnet-4-6 and gemini-3-1-preview?

# MODEL

Good, I have enough data. Now let me also note that you asked about "gemini-3-1-preview" — based on the search results this appears to be **Gemini 3.1 Pro Preview**. Let me clarify that and build the full comparison.

---

## Anthropic Python SDK — PDF Support

Yes, fully supported. The SDK is `anthropic` and PDFs are passed as a `document` content block.

**Method 1 — Inline (base64):**

```python
import anthropic, base64

client = anthropic.Anthropic()

with open("document.pdf", "rb") as f:
    pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                }
            },
            {"type": "text", "text": "Summarize this document."}
        ]
    }]
)
print(response.content[0].text)
```

**Method 2 — Files API (reusable across calls):**

```python
import anthropic

client = anthropic.Anthropic()

# Upload once, reuse the file_id
with open("document.pdf", "rb") as f:
    uploaded = client.beta.files.upload(
        file=("document.pdf", f, "application/pdf")
    )

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "file",
                    "file_id": uploaded.id
                }
            },
            {"type": "text", "text": "What are the key findings?"}
        ]
    }]
)
```

The Files API is particularly valuable when you're asking multiple questions about the same document. Without it, the full PDF is re-sent as tokens on every request. With it, you upload once and subsequent requests reference only a short `file_id`.

**How Claude handles the visual content:** Since each PDF page is converted into an image under the hood, the same image-based token cost calculations apply. Text token costs run 1,500–3,000 tokens per page depending on content density, with standard API pricing and no additional PDF fees. An image uses approximately `width × height / 750` tokens. For most models, the max resized image is capped at 1,568 tokens.

---

## Cost Comparison: 1 MB PDF with Images

A 1 MB image-heavy PDF is roughly **5–10 pages**. Let's use **~8 pages** as a realistic estimate, with each page rendered at the standard vision resolution (~1,568 tokens/page for non-Opus models), plus extracted text (~2,000 tokens/page).

**Estimated input tokens for the PDF: ~28,000–30,000 tokens** (let's use 30K for easy math).Here's the full picture:

---

### Anthropic SDK — How PDFs Work

The `document` content block type handles PDFs natively — no beta header needed anymore. You can pass base64 inline or reference a `file_id` from the Files API (good for multi-turn). Each page is converted into an image, so image-based token cost calculations apply. Text token costs run 1,500–3,000 tokens per page depending on content density, at standard pricing with no additional PDF fees.
