import { useState } from "react";
import { useRouter } from "next/router";
import { RAGResponse } from "../lib/types";
import { authFetch } from "../lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RagPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const response = await authFetch(`${API_URL}/rag/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, k: 4 }),
      });

      if (response.status === 401) {
        router.push("/login");
        return;
      }

      if (response.status === 403) {
        setError("Insufficient scope. Your credential lacks access to this resource.");
        return;
      }

      if (response.status === 422) {
        const detail = await response.json();
        setError(`Validation error: ${JSON.stringify(detail.detail)}`);
        return;
      }

      if (response.status === 503) {
        setError("Backend not ready. Please try again later.");
        return;
      }

      if (!response.ok) {
        setError(`Error: ${response.statusText}`);
        return;
      }

      const data: RAGResponse = await response.json();
      setResult(data);
    } catch (e) {
      setError("Failed to connect to API. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  // Replace [N] markers in the answer text with citation-marker spans.
  function renderAnswer(answer: string) {
    const parts = answer.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      if (/^\[\d+\]$/.test(part)) {
        return (
          <span key={i} data-testid="citation-marker" style={{ color: "#0070f3", fontWeight: "bold" }}>
            {part}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }

  return (
    <main>
      <h1>RAG — Cited Answer</h1>
      <input
        id="rag-question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a recipe question..."
        style={{ width: "100%", marginBottom: 8 }}
      />
      <button id="rag-submit" onClick={submit} disabled={!question || loading}>
        {loading ? "Thinking…" : "Ask"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && (
        <div id="rag-results">
          <p id="rag-answer">{renderAnswer(result.answer)}</p>
          <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
          {result.citations.length > 0 && (
            <ul>
              {result.citations.map((c, i) => (
                <li key={i}>
                  <span data-testid="citation-marker" style={{ color: "#0070f3", fontWeight: "bold" }}>
                    [{i + 1}]
                  </span>{" "}
                  chunk #{c.chunk_id} (score: {c.score.toFixed(3)})
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </main>
  );
}
