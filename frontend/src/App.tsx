import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Archive,
  Bell,
  Box,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Command,
  Download,
  FileSearch,
  Fingerprint,
  GitBranch,
  KeyRound,
  LockKeyhole,
  Menu,
  Network,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./index.css";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
type Workspace = { id: string; name: string; is_demo: boolean };
type Asset = {
  id: string;
  name: string;
  asset_type: string;
  source: string;
  risk: string;
  metadata: Record<string, unknown>;
  created_at: string;
};
type Finding = {
  id: string;
  asset_id: string;
  title: string;
  algorithm: string | null;
  category: string;
  risk: string;
  quantum_relevance: string;
  recommendation: string;
  evidence: string;
  source: string;
};
type Dashboard = {
  workspace: Workspace;
  metrics: Record<string, number>;
  risk_distribution: { name: string; value: number }[];
  algorithm_distribution: { name: string; value: number }[];
  recent_assets: Asset[];
  recommended_actions: Finding[];
};
type Task = {
  id: string;
  title: string;
  concern: string;
  direction: string;
  priority: string;
  status: string;
  notes: string;
};
type Page =
  | "Overview"
  | "Asset Discovery"
  | "Cryptographic Inventory"
  | "Algorithm Intelligence"
  | "Certificate Intelligence"
  | "Dependency Graph"
  | "PQC Readiness"
  | "Migration Planner"
  | "Security Reports"
  | "Settings";
const nav: { name: Page; icon: typeof Activity }[] = [
  { name: "Overview", icon: Activity },
  { name: "Asset Discovery", icon: Upload },
  { name: "Cryptographic Inventory", icon: Archive },
  { name: "Algorithm Intelligence", icon: KeyRound },
  { name: "Certificate Intelligence", icon: Fingerprint },
  { name: "Dependency Graph", icon: Network },
  { name: "PQC Readiness", icon: Sparkles },
  { name: "Migration Planner", icon: GitBranch },
  { name: "Security Reports", icon: FileSearch },
  { name: "Settings", icon: Settings },
];
const riskClass = (risk: string) =>
  `risk risk-${risk.toLowerCase().replace(" ", "-")}`;
const api = async <T,>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok)
    throw new Error((await response.text()) || "Request failed");
  return response.json();
};

function Metric({
  label,
  value,
  icon: Icon,
  tone = "cyan",
}: {
  label: string;
  value: number | string;
  icon: typeof Activity;
  tone?: string;
}) {
  return (
    <article className={`metric metric-${tone}`}>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
      <span className="metric-icon">
        <Icon size={19} />
      </span>
    </article>
  );
}
function Empty({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="empty">
      <CircleDot size={26} />
      <h3>{title}</h3>
      <p>{copy}</p>
    </div>
  );
}
function PanelHeading({
  title,
  subtitle,
  action,
  onClick,
}: {
  title: string;
  subtitle: string;
  action?: string;
  onClick?: () => void;
}) {
  return (
    <div className="panel-head">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action && (
        <button className="link-btn" onClick={onClick}>
          {action}
          <ChevronRight size={15} />
        </button>
      )}
    </div>
  );
}
function SignalRail({ dashboard }: { dashboard: Dashboard }) {
  const m = dashboard.metrics;
  return (
    <section className="signal-rail">
      <div className="signal-intro">
        <span className="pulse-dot" />
        WORKSPACE SIGNALS
      </div>
      <div className="signal-item">
        <small>INVENTORY COVERAGE</small>
        <b>
          {m.assets} <em>assets mapped</em>
        </b>
      </div>
      <div className="signal-item signal-danger">
        <small>PRIORITY EXPOSURE</small>
        <b>
          {m.critical} <em>critical items</em>
        </b>
      </div>
      <div className="signal-item">
        <small>MODERNIZATION</small>
        <b>
          {m.migration_progress}% <em>plan progress</em>
        </b>
      </div>
      <div className="signal-label">EVIDENCE-BACKED</div>
    </section>
  );
}

function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const refresh = async (active = workspace) => {
    if (!active) return;
    const q = `workspace_id=${active.id}`;
    const [d, a, f, t] = await Promise.all([
      api<Dashboard>(`/api/v1/dashboard?${q}`),
      api<Asset[]>(`/api/v1/assets?${q}`),
      api<Finding[]>(`/api/v1/findings?${q}`),
      api<Task[]>(`/api/v1/migrations?${q}`),
    ]);
    setDashboard(d);
    setAssets(a);
    setFindings(f);
    setTasks(t);
  };
  useEffect(() => {
    (async () => {
      try {
        const loaded = await api<Workspace[]>("/api/v1/workspaces");
        const first = loaded[0] ?? null;
        setWorkspace(first);
        if (first) await refresh(first);
      } catch {
        setError(
          "CryptoMap API is unavailable. Start the FastAPI server on port 8000.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  const filteredAssets = useMemo(
    () =>
      assets.filter((a) => a.name.toLowerCase().includes(search.toLowerCase())),
    [assets, search],
  );
  const filteredFindings = useMemo(
    () =>
      findings.filter((f) =>
        `${f.title} ${f.algorithm ?? ""}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [findings, search],
  );
  const upload = async () => {
    if (!file || !workspace) return;
    const form = new FormData();
    form.append("file", file);
    setUploading(true);
    setError("");
    try {
      const result = await api<{ notice: string }>(
        `/api/v1/scans/upload?workspace_id=${workspace.id}`,
        { method: "POST", body: form },
      );
      setNotice(result.notice);
      setFile(null);
      await refresh();
      setPage("Cryptographic Inventory");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message.replaceAll('"', "")
          : "Upload failed",
      );
    } finally {
      setUploading(false);
    }
  };
  const setStatus = async (task: Task, status: string) => {
    try {
      await api(
        `/api/v1/migrations/${task.id}/status?status=${encodeURIComponent(status)}`,
        { method: "POST" },
      );
      setNotice(`Migration task updated to ${status}.`);
      await refresh();
    } catch {
      setError("Could not update migration task.");
    }
  };
  const download = async (path: string, filename: string) => {
    if (!workspace) return;
    const response = await fetch(`${API}${path}?workspace_id=${workspace.id}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };
  const content = () => {
    if (loading)
      return (
        <div className="loading-grid">
          <span />
          <span />
          <span />
          <span />
        </div>
      );
    if (!workspace || !dashboard)
      return (
        <Empty
          title="API connection required"
          copy="Start the backend to load workspace intelligence."
        />
      );
    if (page === "Overview")
      return <Overview dashboard={dashboard} setPage={setPage} />;
    if (page === "Asset Discovery")
      return (
        <Discovery
          file={file}
          setFile={setFile}
          upload={upload}
          uploading={uploading}
        />
      );
    if (page === "Cryptographic Inventory")
      return <Inventory assets={filteredAssets} />;
    if (
      page === "Algorithm Intelligence" ||
      page === "Certificate Intelligence"
    )
      return (
        <Findings
          findings={filteredFindings}
          certificateOnly={page === "Certificate Intelligence"}
        />
      );
    if (page === "Dependency Graph") return <Graph workspace={workspace} />;
    if (page === "PQC Readiness") return <Pqc workspace={workspace} />;
    if (page === "Migration Planner")
      return <Migrations tasks={tasks} setStatus={setStatus} />;
    if (page === "Security Reports")
      return <Reports dashboard={dashboard} download={download} />;
    return <SettingsView workspace={workspace} />;
  };
  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">
            <LockKeyhole size={19} />
          </span>
          <span>
            <b>CryptoMap</b>
            <small>Cryptographic intelligence</small>
          </span>
        </div>
        <div className="workspace">
          <span className="workspace-dot" />
          <div>
            <small>WORKSPACE</small>
            <b>{workspace?.name ?? "Loading workspace"}</b>
            {workspace?.is_demo && <em>SYNTHETIC DEMO</em>}
          </div>
          <ChevronDown size={15} />
        </div>
        <nav>
          {nav.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              onClick={() => {
                setPage(name);
                setSidebarOpen(false);
              }}
            >
              <Icon size={17} />
              <span>{name}</span>
              {name === "Migration Planner" && tasks.length > 0 && (
                <i>{tasks.length}</i>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <ShieldCheck size={16} />
          <div>
            <b>Authorized analysis only</b>
            <span>Uploaded data stays in your workspace.</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <button
            className="icon-btn mobile-menu"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <Menu size={19} />
          </button>
          <div className="search">
            <Search size={17} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search assets, algorithms, findings..."
            />
            <kbd>
              <Command size={11} /> K
            </kbd>
          </div>
          <div className="top-actions">
            <button className="icon-btn" title="Notifications">
              <Bell size={18} />
              <span className="notification" />
            </button>
            <span className="avatar">AY</span>
            <div className="profile">
              <b>Abhishek Yadav</b>
              <small>Security Architect</small>
            </div>
            <ChevronDown size={15} />
          </div>
        </header>
        <section className="page-wrap">
          <div className="page-title">
            <div className="title-main">
              <div className="section-code">
                <span />
                CRYPTO INTELLIGENCE / {page}
              </div>
              <p>
                {workspace?.is_demo
                  ? "SYNTHETIC DEMO WORKSPACE"
                  : "AUTHORIZED WORKSPACE"}
              </p>
              <h1>{page}</h1>
            </div>
            <div className="title-side">
              <span className="analysis-live">
                <i />
                LOCAL ANALYSIS MODE
              </span>
              {page === "Asset Discovery" && (
                <button
                  className="primary"
                  onClick={upload}
                  disabled={!file || uploading}
                >
                  <Upload size={16} />
                  {uploading ? "Analyzing..." : "Analyze upload"}
                </button>
              )}
            </div>
          </div>
          {error && (
            <div className="banner banner-error">
              <AlertTriangle size={17} />
              {error}
              <button onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="banner">
              <CheckCircle2 size={17} />
              {notice}
              <button onClick={() => setNotice("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {content()}
        </section>
      </main>
    </div>
  );
}

function Overview({
  dashboard,
  setPage,
}: {
  dashboard: Dashboard;
  setPage: (page: Page) => void;
}) {
  const m = dashboard.metrics;
  return (
    <>
      <div className="metric-grid">
        <Metric label="Cryptographic assets" value={m.assets} icon={Box} />
        <Metric
          label="Critical risk assets"
          value={m.critical}
          icon={AlertTriangle}
          tone="red"
        />
        <Metric
          label="Weak or deprecated"
          value={m.weak}
          icon={KeyRound}
          tone="amber"
        />
        <Metric
          label="PQC readiness"
          value={`${m.pqc_score}/100`}
          icon={Sparkles}
          tone="green"
        />
        <Metric
          label="Quantum exposed"
          value={m.quantum_exposed}
          icon={Fingerprint}
          tone="violet"
        />
        <Metric
          label="Migration progress"
          value={`${m.migration_progress}%`}
          icon={GitBranch}
        />
      </div>
      <SignalRail dashboard={dashboard} />
      <div className="overview-grid">
        <section className="panel chart-panel">
          <PanelHeading
            title="Algorithm intelligence"
            subtitle="Stored findings by detected algorithm"
            action="View inventory"
            onClick={() => setPage("Algorithm Intelligence")}
          />
          <div className="chart">
            <ResponsiveContainer width="100%" height={235}>
              <BarChart data={dashboard.algorithm_distribution}>
                <XAxis dataKey="name" stroke="#8290a4" fontSize={11} />
                <YAxis stroke="#8290a4" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "#15202b",
                    border: "1px solid #2a3a4c",
                    borderRadius: 6,
                  }}
                />
                <Bar dataKey="value" radius={[3, 3, 0, 0]} fill="#20c7e8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel chart-panel">
          <PanelHeading
            title="Risk distribution"
            subtitle="Evidence-backed findings"
          />
          <div className="risk-chart">
            <ResponsiveContainer width="56%" height={220}>
              <PieChart>
                <Pie
                  data={dashboard.risk_distribution}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={58}
                  outerRadius={82}
                  paddingAngle={3}
                >
                  {dashboard.risk_distribution.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={
                        ["#ed5d66", "#f0ae50", "#20c7e8", "#48b888", "#7e8ca0"][
                          index % 5
                        ]
                      }
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#15202b",
                    border: "1px solid #2a3a4c",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="legend">
              {dashboard.risk_distribution.map((item, index) => (
                <span key={item.name}>
                  <i
                    style={{
                      background: [
                        "#ed5d66",
                        "#f0ae50",
                        "#20c7e8",
                        "#48b888",
                        "#7e8ca0",
                      ][index % 5],
                    }}
                  />
                  {item.name}
                  <b>{item.value}</b>
                </span>
              ))}
            </div>
          </div>
        </section>
      </div>
      <div className="bottom-grid">
        <section className="panel">
          <PanelHeading
            title="Recommended actions"
            subtitle="Prioritized from stored findings"
            action="Review findings"
            onClick={() => setPage("Algorithm Intelligence")}
          />
          {dashboard.recommended_actions.length ? (
            <div className="action-list">
              {dashboard.recommended_actions.map((item) => (
                <div key={item.id}>
                  <span className={riskClass(item.risk)}>{item.risk}</span>
                  <div>
                    <b>{item.title}</b>
                    <p>{item.recommendation}</p>
                  </div>
                  <ChevronRight size={17} />
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="No priority actions"
              copy="Upload an authorized file to produce analysis findings."
            />
          )}
        </section>
        <section className="panel">
          <PanelHeading
            title="Recent discoveries"
            subtitle="Authorized uploads and labeled demo data"
            action="Open discovery"
            onClick={() => setPage("Asset Discovery")}
          />
          {dashboard.recent_assets.map((asset) => (
            <div className="recent" key={asset.id}>
              <span className="asset-icon">
                <Box size={15} />
              </span>
              <div>
                <b>{asset.name}</b>
                <p>
                  {asset.asset_type} · {asset.source}
                </p>
              </div>
              <span className={riskClass(asset.risk)}>{asset.risk}</span>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
function Discovery({
  file,
  setFile,
  upload,
  uploading,
}: {
  file: File | null;
  setFile: (file: File | null) => void;
  upload: () => void;
  uploading: boolean;
}) {
  return (
    <div className="discovery-layout">
      <section className="panel drop-panel">
        <span className="scan-glyph">
          <Upload size={29} />
        </span>
        <h2>Analyze an authorized file</h2>
        <p>
          Upload only configurations, manifests, or certificates you are
          authorized to inspect. Files are parsed as untrusted data and never
          executed.
        </p>
        <label className="file-picker">
          <input
            type="file"
            accept=".pem,.crt,.cer,.json,.yaml,.yml,.txt,.conf,.config"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <>
              <CheckCircle2 size={17} />
              {file.name}
            </>
          ) : (
            <>
              <Upload size={17} />
              Choose a certificate or configuration
            </>
          )}
        </label>
        <small>
          Supported: PEM, CRT, CER, JSON, YAML, TXT, CONF · Maximum 2 MB
        </small>
        {file && (
          <button className="primary" onClick={upload} disabled={uploading}>
            {uploading ? "Analyzing safely..." : "Start analysis"}
          </button>
        )}
      </section>
      <section className="panel parser-panel">
        <PanelHeading
          title="Discovery boundaries"
          subtitle="CryptoMap discovery is intentionally constrained"
        />
        <ul>
          <li>
            <CheckCircle2 />
            Only uploaded or explicitly authorized files are analyzed.
          </li>
          <li>
            <CheckCircle2 />
            Uploaded content is never executed or used to scan external systems.
          </li>
          <li>
            <CheckCircle2 />
            Configuration evidence is not equivalent to complete enterprise
            discovery.
          </li>
          <li>
            <CheckCircle2 />
            Private keys are not stored, logged, or reported.
          </li>
        </ul>
      </section>
    </div>
  );
}
function Inventory({ assets }: { assets: Asset[] }) {
  return (
    <section className="panel table-panel">
      <PanelHeading
        title="Cryptographic asset inventory"
        subtitle="Workspace-scoped assets with source and assessed risk"
      />
      {assets.length ? (
        <table>
          <thead>
            <tr>
              <th>Asset</th>
              <th>Type</th>
              <th>Source</th>
              <th>Risk</th>
              <th>Discovered</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.id}>
                <td>
                  <b>{asset.name}</b>
                </td>
                <td>{asset.asset_type}</td>
                <td>
                  <span className="source-tag">{asset.source}</span>
                </td>
                <td>
                  <span className={riskClass(asset.risk)}>{asset.risk}</span>
                </td>
                <td>{new Date(asset.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <Empty
          title="No assets found"
          copy="Use Asset Discovery to analyze an authorized file."
        />
      )}
    </section>
  );
}
function Findings({
  findings,
  certificateOnly,
}: {
  findings: Finding[];
  certificateOnly: boolean;
}) {
  const records = certificateOnly
    ? findings.filter((item) => item.category === "certificate")
    : findings;
  return (
    <section className="panel findings-panel">
      <PanelHeading
        title={
          certificateOnly
            ? "Certificate intelligence"
            : "Algorithm intelligence"
        }
        subtitle={
          certificateOnly
            ? "Parsing, validity and policy findings from uploaded certificates"
            : "Transparent rule classification; quantum exposure is not a claim of current breakage"
        }
      />
      {records.length ? (
        <div className="findings">
          {records.map((finding) => (
            <article key={finding.id}>
              <div className="finding-top">
                <span className={riskClass(finding.risk)}>{finding.risk}</span>
                <span>{finding.algorithm ?? finding.category}</span>
                <span className="quantum">{finding.quantum_relevance}</span>
              </div>
              <h3>{finding.title}</h3>
              <p>{finding.evidence}</p>
              <div className="recommend">
                <b>Recommended action</b>
                {finding.recommendation}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="No matching intelligence"
          copy="Upload a supported certificate or configuration to produce evidence-backed findings."
        />
      )}
    </section>
  );
}
function Graph({ workspace }: { workspace: Workspace }) {
  const [graph, setGraph] = useState<{
    nodes: Node[];
    edges: Edge[];
    notice: string;
  } | null>(null);
  useEffect(() => {
    api<{
      nodes: { id: string; label: string; type: string; risk: string }[];
      edges: { id: string; source: string; target: string; label: string }[];
      notice: string;
    }>(`/api/v1/dependencies?workspace_id=${workspace.id}`)
      .then((data) =>
        setGraph({
          nodes: data.nodes.map((node, index) => ({
            id: node.id,
            position: { x: (index % 3) * 260, y: Math.floor(index / 3) * 150 },
            data: {
              label: (
                <div className="flow-node">
                  <small>{node.type}</small>
                  <b>{node.label}</b>
                  <span className={riskClass(node.risk)}>{node.risk}</span>
                </div>
              ),
            },
            style: {
              border: "1px solid #30465c",
              background: "#15202b",
              borderRadius: 8,
              color: "#e5edf5",
              width: 205,
            },
          })),
          edges: data.edges.map((edge) => ({
            ...edge,
            animated: false,
            style: { stroke: "#23c7e8" },
            labelStyle: { fill: "#9bacbd" },
          })),
          notice: data.notice,
        }),
      )
      .catch(() => undefined);
  }, [workspace.id]);
  return (
    <section className="panel graph-panel">
      <PanelHeading
        title="Crypto dependency intelligence graph"
        subtitle="Relationships are generated only from stored, evidenced dependencies."
      />
      {graph ? (
        <>
          <div className="graph">
            <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView>
              <Background color="#233449" gap={18} />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
          {!graph.edges.length && (
            <div className="graph-note">
              <Network size={17} />
              No evidenced dependencies recorded yet. CryptoMap does not invent
              unknown relationships.
            </div>
          )}
        </>
      ) : (
        <div className="loading-grid">
          <span />
          <span />
        </div>
      )}
    </section>
  );
}
function Pqc({ workspace }: { workspace: Workspace }) {
  const [data, setData] = useState<{
    readiness_score: number;
    methodology: string;
    exposed_findings: Finding[];
    standards: { name: string; reference: string }[];
    next_steps: string[];
  } | null>(null);
  useEffect(() => {
    api<typeof data>(`/api/v1/pqc?workspace_id=${workspace.id}`)
      .then(setData)
      .catch(() => undefined);
  }, [workspace.id]);
  if (!data)
    return (
      <div className="loading-grid">
        <span />
        <span />
      </div>
    );
  return (
    <div className="pqc-layout">
      <section className="panel score-card">
        <p>PQC READINESS SCORE</p>
        <div className="score">
          <b>{data.readiness_score}</b>
          <span>/ 100</span>
        </div>
        <div className="score-track">
          <i style={{ width: `${data.readiness_score}%` }} />
        </div>
        <small>{data.methodology}</small>
      </section>
      <section className="panel">
        <PanelHeading
          title="Post-quantum exposure"
          subtitle="Public-key findings needing longer-term migration planning"
        />
        {data.exposed_findings.length ? (
          data.exposed_findings.map((item) => (
            <div className="exposure" key={item.id}>
              <Fingerprint size={18} />
              <div>
                <b>{item.title}</b>
                <p>{item.recommendation}</p>
              </div>
              <span className={riskClass(item.risk)}>{item.risk}</span>
            </div>
          ))
        ) : (
          <Empty
            title="No recorded quantum exposure"
            copy="This reflects stored findings only, not a full cryptographic inventory."
          />
        )}
      </section>
      <section className="panel">
        <PanelHeading
          title="NIST PQC references"
          subtitle="Standards reference, not automatic replacement guidance"
        />
        {data.standards.map((item) => (
          <div className="standard" key={item.name}>
            <Sparkles size={18} />
            <b>{item.name}</b>
            <span>{item.reference}</span>
          </div>
        ))}
        <hr />
        {data.next_steps.map((step) => (
          <p className="next" key={step}>
            <CheckCircle2 size={15} />
            {step}
          </p>
        ))}
      </section>
    </div>
  );
}
function Migrations({
  tasks,
  setStatus,
}: {
  tasks: Task[];
  setStatus: (task: Task, status: string) => void;
}) {
  return (
    <section className="panel table-panel">
      <PanelHeading
        title="Cryptographic modernization planner"
        subtitle="Planning records only. CryptoMap never modifies production configurations."
      />
      {tasks.length ? (
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Modernization direction</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id}>
                <td>
                  <b>{task.title}</b>
                  <p>{task.concern}</p>
                </td>
                <td>
                  <span className={riskClass(task.priority)}>
                    {task.priority}
                  </span>
                </td>
                <td>
                  <select
                    value={task.status}
                    onChange={(e) => setStatus(task, e.target.value)}
                  >
                    {[
                      "Identified",
                      "Planned",
                      "In Progress",
                      "Under Review",
                      "Completed",
                    ].map((status) => (
                      <option key={status}>{status}</option>
                    ))}
                  </select>
                </td>
                <td>{task.direction}</td>
                <td>
                  <ChevronRight size={17} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <Empty
          title="No migration tasks"
          copy="Tasks appear after risk and dependency assessments."
        />
      )}
    </section>
  );
}
function Reports({
  dashboard,
  download,
}: {
  dashboard: Dashboard;
  download: (path: string, filename: string) => void;
}) {
  return (
    <div className="reports">
      <section className="panel report-card">
        <span className="report-icon">
          <FileSearch size={26} />
        </span>
        <div>
          <p>EXECUTIVE SUMMARY</p>
          <h2>Cryptographic intelligence report</h2>
          <p>
            Generate exports using stored workspace assets, findings, and
            documented limitations.
          </p>
        </div>
        <div className="report-actions">
          <button
            className="primary"
            onClick={() =>
              download("/api/v1/reports/summary.pdf", "cryptomap-summary.pdf")
            }
          >
            <Download size={16} />
            PDF report
          </button>
          <button
            className="secondary"
            onClick={() =>
              download("/api/v1/reports/findings.csv", "cryptomap-findings.csv")
            }
          >
            <Download size={16} />
            CSV findings
          </button>
        </div>
      </section>
      <section className="panel methodology">
        <PanelHeading
          title="Report scope"
          subtitle="Every report includes source and limitation context"
        />
        <ul>
          <li>
            <CheckCircle2 />
            {dashboard.metrics.assets} stored cryptographic assets
          </li>
          <li>
            <CheckCircle2 />
            {dashboard.metrics.weak} weak or deprecated findings
          </li>
          <li>
            <CheckCircle2 />
            {dashboard.metrics.quantum_exposed} future quantum-vulnerable
            dependencies
          </li>
          <li>
            <CheckCircle2 />
            Synthetic demo records remain explicitly labeled
          </li>
        </ul>
      </section>
    </div>
  );
}
function SettingsView({ workspace }: { workspace: Workspace }) {
  return (
    <div className="settings-grid">
      <section className="panel">
        <PanelHeading
          title="Workspace boundary"
          subtitle="Data separation and demo labeling"
        />
        <div className="setting-row">
          <div>
            <b>{workspace.name}</b>
            <p>
              {workspace.is_demo
                ? "This is a synthetic demonstration workspace."
                : "Authorized workspace."}
            </p>
          </div>
          <span className="source-tag">
            {workspace.is_demo ? "Synthetic demo" : "Authorized"}
          </span>
        </div>
      </section>
      <section className="panel">
        <PanelHeading
          title="Local development configuration"
          subtitle="Environment-driven settings"
        />
        <div className="setting-row">
          <div>
            <b>Database</b>
            <p>
              SQLite is enabled for local development. PostgreSQL can be set
              through CRYPTOMAP_DATABASE_URL.
            </p>
          </div>
        </div>
        <div className="setting-row">
          <div>
            <b>Upload boundary</b>
            <p>
              2 MB size limit and supported configuration/certificate formats
              only.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
export default App;
