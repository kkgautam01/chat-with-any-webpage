# Chat with Any Webpage (RAG Demo)

## 🚀 Overview
A simple AI-powered app that lets users **chat with the content of any webpage**.  
Just paste a URL, and the system enables question-answering based strictly on that page.

---

## ⚙️ How It Works

1. **Input URL**
   - User provides a webpage link

2. **Content Extraction**
   - Scrapes and cleans main content (removes ads, nav, scripts, etc.)

3. **Chunking**
   - Splits content into smaller text chunks for better processing

4. **Embeddings**
   - Converts text into vector representations (semantic meaning)

5. **Vector Storage**
   - Stores embeddings in FAISS for fast similarity search

6. **Retrieval (RAG)**
   - Finds most relevant chunks based on user query
   - Uses:
     - Similarity Search
     - MMR (diversity)
     - HyDE (query expansion)

7. **LLM Response**
   - Sends retrieved context to LLM
   - Generates accurate answers based only on page content

---

## 💡 Features

- Chat with **any webpage**
- Context-aware Q&A
- Summarization support
- Smart retrieval (MMR + HyDE)
- Clean UI with typing effect
- No external knowledge leakage (strict RAG)

---

## 🧠 Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, JS
- **LLM:** Groq (LLaMA 3), Optional: OpenApi, Gemini, Claude
- **Embeddings:** HuggingFace (MiniLM)
- **Vector DB:** FAISS

---

## 🎯 Use Cases

- Read and understand long articles quickly
- Extract key points from blogs/docs
- Legal/terms/privacy page analysis
- Research assistance

---

## ⚡ Example Queries

- "Summarize this page"
- "What data is collected?"
- "Explain key terms"
- "List main points"

---

## 📌 Note

This is a **demo RAG system** built to showcase:
- Retrieval + LLM integration
- Context-based answering
- Real-world AI application

---

## 👨‍💻 Author

Built as a demo project to showcase AI + RAG capabilities.