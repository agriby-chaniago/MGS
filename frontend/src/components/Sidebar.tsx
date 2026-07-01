import { useEffect, useState } from "react";
import { deleteDataset, listDatasets } from "../api/datasets";
import type { Dataset } from "../api/types";
import { useAuth } from "../context/AuthContext";

interface Props {
  onSelectDataset: (dataset: Dataset) => void;
  activeDatasetId: string | null;
  auditInProgress: boolean;
}

export default function Sidebar({ onSelectDataset, activeDatasetId, auditInProgress }: Props) {
  const { plan, logout } = useAuth();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      setDatasets(await listDatasets());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleDelete(id: string) {
    if (auditInProgress) return;
    await deleteDataset(id);
    await refresh();
  }

  return (
    <aside className="sidebar">
      <div className="plan-badge">Paket: {plan?.toUpperCase() ?? "?"}</div>
      <button onClick={logout}>Logout</button>
      <h3>Riwayat Dataset</h3>
      {loading && <p>Memuat...</p>}
      <ul>
        {datasets.map((d) => (
          <li key={d.id} className={d.id === activeDatasetId ? "active" : ""}>
            <button
              disabled={auditInProgress}
              onClick={() => onSelectDataset(d)}
              title={`${d.total_images} gambar`}
            >
              {d.name}
            </button>
            <button disabled={auditInProgress} onClick={() => handleDelete(d.id)}>
              🗑
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
