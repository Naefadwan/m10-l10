import { useState } from "react";
import { useRouter } from "next/router";
import { ExtractResponse } from "../lib/types";
import { authFetch } from "../lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ExtractPage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    setResult(null);
    try {
      const response = await authFetch(`${API_URL}/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
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

      const data: ExtractResponse = await response.json();
      setResult(data);
    } catch (e) {
      setError("Failed to connect to API. Is the backend running?");
    }
  }

  return (
    <main>
      <h1>Extract — Named Entity Recognition</h1>
      <textarea
        id="extract-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter text to extract entities from..."
        rows={5}
      />
      <br />
      <button id="extract-submit" onClick={submit} disabled={!text}>
        Extract
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && result.entities.length > 0 && (
        <div id="extract-results">
          {result.entities.map((entity, index) => (
            <span
              key={index}
              data-testid="entity-span"
              title={entity.label}
              style={{ marginRight: 8, padding: "2px 6px", border: "1px solid #888", borderRadius: 4 }}
            >
              {entity.text} <em>({entity.label})</em>
            </span>
          ))}
        </div>
      )}

      {result && result.entities.length === 0 && (
        <p>No entities found.</p>
      )}
    </main>
  );
}
