import { useState } from "react";

// TODO: import { KGResponse } from "../lib/types".

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function KgPage() {
  const [question, setQuestion] = useState("");
  // TODO: track result + error state.

  async function submit() {
    // TODO:
    // 1. POST to `${API_URL}/kg/query` with JSON body { question }.
    // 2. Handle 422 (unsupported question) — surface the supported_patterns
    //    list to the user from the response detail.
    // 3. Render the cypher and table of rows.
  }

  return (
    <main>
      <h1>Knowledge Graph — Recipe Query</h1>
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g. Find Sichuan recipes"
      />
      <button onClick={submit} disabled={!question}>Ask</button>
      {/* TODO: render cypher in a <pre>, rows in a <table> with each
                row having `data-testid="kg-row"`. */}
    </main>
  );
}
