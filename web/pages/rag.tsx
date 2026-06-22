import { useState } from "react";

// TODO: import { RAGResponse } from "../lib/types".

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RagPage() {
  const [question, setQuestion] = useState("");
  // TODO: track result + error state + loading.

  async function submit() {
    // TODO:
    // 1. POST to `${API_URL}/rag/answer` with JSON body { question, k: 4 }.
    // 2. Handle 422 + 503 distinctly.
    // 3. Render the answer + inline [N] citation markers. Each citation
    //    marker element MUST have `data-testid="citation-marker"` so
    //    Playwright can locate it.
  }

  return (
    <main>
      <h1>RAG — Cited Answer</h1>
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a recipe question..."
      />
      <button onClick={submit} disabled={!question}>Ask</button>
      {/* TODO: render answer + citations with data-testid markers. */}
    </main>
  );
}
