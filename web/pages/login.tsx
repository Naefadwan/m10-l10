import { useState, FormEvent } from "react";
import { useRouter } from "next/router";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (res.status === 401) {
        const detail = await res.json().catch(() => ({}));
        setError(detail.detail || "Invalid username or password");
        return;
      }

      if (!res.ok) {
        setError(`Login failed (${res.status})`);
        return;
      }

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      router.push("/extract");
    } catch {
      setError("Failed to connect to API. Is the backend running?");
    }
  }

  return (
    <main>
      <h1>Login</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username">Username</label>
          <br />
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <br />
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <br />
        <button type="submit">Sign in</button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}
    </main>
  );
}
