import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, Card, Input, Logo } from "../components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Email atau password salah.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <Card className="p-8">
          <h1 className="mb-6 text-xl font-semibold text-white">Masuk ke akun kamu</h1>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && <p className="text-sm text-rose-400">{error}</p>}
            <Button type="submit" disabled={loading} className="mt-1 w-full">
              {loading ? "Masuk..." : "Login"}
            </Button>
          </form>
        </Card>
        <p className="mt-6 text-center text-sm text-slate-400">
          Belum punya akun?{" "}
          <Link to="/register" className="font-medium text-violet-400 hover:text-violet-300">
            Daftar
          </Link>
        </p>
      </div>
    </div>
  );
}
