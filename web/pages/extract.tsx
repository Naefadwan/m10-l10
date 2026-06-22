import { useState } from "react";

// TODO: import { ExtractResponse } from "../lib/types" once you declare it.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ExtractPage() {
  const [text, setText] = useState("");
  // TODO: track the result as ExtractResponse | null and an error state.

  async function submit() {
    // TODO:
    // 1. POST to `${API_URL}/extract` with JSON body { text }.
    // 2. Handle 422 (validation) and 503 (backend not ready) distinctly.
    // 3. Parse the response and put it on state.
  }

  return (
    <main>
      <h1>Extract — Named Entity Recognition</h1>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      <button onClick={submit} disabled={!text}>Extract</button>
      {/* TODO: render entity spans with `data-testid="entity-span"` so
                Playwright can find them. */}
    </main>
  );
}
