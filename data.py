import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings


import requests
from bs4 import BeautifulSoup

chat_history = []


# ── scraping ──────────────────────────────────────────────────────────────────

# Tags that NEVER contain real page content — always noise
NOISE_TAGS = [
    "script", "style", "nav", "footer", "header", "aside",
    "noscript", "iframe", "form", "button", "figure", "figcaption",
]

# CSS class/id fragments that signal promotional / navigation blocks
NOISE_PATTERNS = [
    "nav", "menu", "sidebar", "footer", "header", "breadcrumb",
    "promo", "banner", "ad-", "cookie", "consent", "related",
    "recommend", "signup", "newsletter", "social", "share",
    "pagination", "tag-cloud", "widget", "sticky",
]


def _is_noisy(tag) -> bool:
    """Return True if a tag looks like nav/promo/sidebar noise."""
    for attr in (tag.get("class", []) or []) + [tag.get("id", "") or ""]:
        attr_str = attr.lower() if isinstance(attr, str) else " ".join(attr).lower()
        if any(p in attr_str for p in NOISE_PATTERNS):
            return True
    return False


def _fetch_with_requests(url: str) -> str:
    """Fast path: plain HTTP fetch. Works for static/SSR pages."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    res = requests.get(url, headers=headers, timeout=20)
    res.raise_for_status()
    return res.text


def _fetch_with_playwright(url: str) -> str:
    """
    Slow path: headless browser — use when the page is JS-rendered.
    Requires: pip install playwright && playwright install chromium
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30_000)
        # Give JS frameworks extra time to render content
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
    return html


def _html_to_text(html: str) -> str:
    """
    Strip all noise from HTML and return clean body text.
    Strategy:
      1. Remove hard-noise tags entirely
      2. Remove blocks whose class/id looks like nav/promo
      3. Prefer <article> or <main>; fall back to <body>
      4. Collapse whitespace
    """
    soup = BeautifulSoup(html, "lxml")

    # Step 1 — remove tag types that never hold content
    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Step 2 — collect noisy tags first, THEN decompose.
    # Decomposing inside find_all() iteration detaches children already
    # queued in the iterator — their .attrs becomes None, causing
    #   AttributeError: 'NoneType' object has no attribute 'get'
    noisy_tags = [t for t in soup.find_all(True) if _is_noisy(t)]
    for t in noisy_tags:
        t.decompose()

    # Step 3 — find the most specific content container
    content = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", {"id": "content"})
        or soup.find("div", {"class": lambda c: c and "content" in " ".join(c).lower()})
        or soup.body
    )

    if not content:
        raise ValueError("Could not locate any content in the page.")

    text = content.get_text(" ", strip=True)
    text = " ".join(text.split())   # collapse all whitespace
    return text


def load_files(url: str) -> list[Document]:
    """
    Try requests first (fast). If the result looks JS-gated
    (very short text or contains typical SSR placeholders),
    fall back to Playwright.
    """
    html = _fetch_with_requests(url)
    text = _html_to_text(html)

    # Heuristic: if we got less than 300 chars the page is probably JS-rendered
    # if len(text) < 300:
    #     try:
    #         html = _fetch_with_playwright(url)
    #         text = _html_to_text(html)
    #     except Exception as e:
    #         raise ValueError(
    #             f"Page appears JS-rendered but Playwright failed: {e}\n"
    #             "Install it with: pip install playwright && playwright install chromium"
    #         )

    if not text.strip():
        raise ValueError("Could not extract any text from that URL.")

    print(f"[INFO] Extracted {len(text):,} characters from {url}")
    return [Document(page_content=text)]


# ── chunking ──────────────────────────────────────────────────────────────────

def split(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    print(f"[INFO] Split into {len(chunks)} chunks")
    return chunks


# ── embeddings ────────────────────────────────────────────────────────────────

def embed():
    if os.environ.get("ENV_RAG") != 'prod':
        return OllamaEmbeddings(model="mxbai-embed-large")

    google_api_key=os.environ.get("GEMINI_API_KEY")
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=google_api_key
    )

    # return HuggingFaceEmbeddings(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2"
    # )

def get_llm():
    # return ChatGoogleGenerativeAI(
    #     model="gemini-2.5-flash",
    #     google_api_key=os.environ["GROQ_API_KEY"]
    # )
    if os.environ.get("ENV_RAG") != 'prod':
        return ChatOllama(model="llama3:8b")

    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.environ["GROQ_API_KEY"]
    )

# ── vector store ──────────────────────────────────────────────────────────────

def save(chunks: list[Document], embeddings) -> Chroma:
    return Chroma.from_documents(chunks, embeddings)


def process(url: str) -> Chroma:
    docs   = load_files(url)
    chunks = split(docs)
    embs   = embed()
    return save(chunks, embs)


# ── retrieval ─────────────────────────────────────────────────────────────────

def mmr_search(vector_store: Chroma, query: str, k: int = 12) -> list[Document]:
    return vector_store.max_marginal_relevance_search(
        query, k=k, fetch_k=25, lambda_mult=0.55
    )


def similarity_search(vector_store: Chroma, query: str, k: int = 12) -> list[Document]:
    return vector_store.similarity_search(query, k=k)


def merge_results(a: list[Document], b: list[Document]) -> list[Document]:
    seen, merged = set(), []
    for doc in a + b:
        key = doc.page_content.strip()
        if key not in seen:
            seen.add(key)
            merged.append(doc)
    return merged


def retrieve(vector_store: Chroma, query: str, llm)-> list[Document]:
    """
    Dual-path retrieval:
      Path A — embed question directly via MMR  (reliable baseline)
      Path B — HyDE: embed a hypothetical answer (catches paraphrase/concept gaps)
    Merge and cap at 7 chunks.
    """
    direct_docs = mmr_search(vector_store, query, k=12)

    hyde_prompt = (
        "Write one short paragraph that directly answers the question below. "
        "Be factual and concise. Do not say you don't know.\n\n"
        f"Question: {query}\n\nAnswer:"
    )
    hypothetical  = llm.invoke(hyde_prompt).content.strip()
    hyde_docs     = similarity_search(vector_store, hypothetical, k=12)

    return merge_results(direct_docs, hyde_docs)[:7]


# ── context assembly ──────────────────────────────────────────────────────────

def build_context(docs: list[Document], max_chars: int = 3500) -> str:
    raw = "\n\n".join(d.page_content for d in docs)
    if len(raw) <= max_chars:
        return raw
    truncated   = raw[:max_chars]
    last_period = truncated.rfind(". ")
    return truncated[: last_period + 1] if last_period != -1 else truncated


# ── main query function ───────────────────────────────────────────────────────

def query_llm(vector_store, query: str) -> str:
    if vector_store is None:
        return "Please load a URL first before asking questions."

    llm = get_llm()

    chat_history.append(f"User: {query}")
    history_text = "\n".join(chat_history[-8:])

    docs = retrieve(vector_store, query, llm)

    if not docs:
        return "I couldn't find relevant information in the page content. Try rephrasing your question."

    context = build_context(docs)

    prompt = f"""You are a helpful assistant. Answer the user's question using ONLY the webpage content provided below.

Rules:
- Cover ALL aspects: data collection, usage, sharing, cookies, user rights, legal terms
- Do NOT skip sections
- Use direct, factual statements (no generic phrases)
- Use "-" bullets only
- Ensure nothing important is missing
- If any important section is missing, expand the answer before finishing

### Webpage Content:
{context}

### Conversation History:
{history_text}

### Question:
{query}

Answer in 2-5 clear sentences:"""

    response = llm.invoke(prompt)
    answer   = response.content.strip()

    if len(answer) < 20:
        answer = f"Here is the most relevant excerpt:\n\n{context[:600]}"

    chat_history.append(f"Assistant: {answer}")
    return answer