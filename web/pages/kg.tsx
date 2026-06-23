import { useState } from "react";
import { KGResponse } from "../lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function KgPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<KGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [patterns, setPatterns] = useState<string[] | null>(null);

  async function submit() {
    setError(null);
    setResult(null);
    setPatterns(null);
    try {
      const response = await fetch(`${API_URL}/kg/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (response.status === 422) {
        const detail = await response.json();
        // Surface the supported_patterns list to the user.
        const d = detail.detail ?? detail;
        if (d.supported_patterns) {
          setPatterns(d.supported_patterns);
        }
        setError(`Unsupported question. Try one of the supported patterns below.`);
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

      const data: KGResponse = await response.json();
      setResult(data);
    } catch (e) {
      setError("Failed to connect to API. Is the backend running?");
    }
  }

  return (
    <main>
      <h1>Knowledge Graph — Recipe Query</h1>
      <input
        id="kg-question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g. Find Sichuan recipes"
        style={{ width: "100%", marginBottom: 8 }}
      />
      <button id="kg-submit" onClick={submit} disabled={!question}>
        Ask
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {patterns && (
        <ul>
          {patterns.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ul>
      )}

      {result && (
        <div id="kg-results">
          <pre id="kg-cypher">{result.cypher}</pre>
          <p>{result.count} row{result.count !== 1 ? "s" : ""}</p>
          {result.rows.length > 0 && (
            <table>
              <thead>
                <tr>
                  {Object.keys(result.rows[0]).map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i} data-testid="kg-row">
                    {Object.values(row).map((val, j) => (
                      <td key={j}>{String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </main>
  );
}
