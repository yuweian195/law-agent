import { useEffect, useMemo, useState } from "react";
import { fetchReview, fetchReviews } from "./api";
import type { ReviewDetail, ReviewListItem, RiskLevel } from "./types";

const RISK_LABEL: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

const TYPE_LABEL: Record<string, string> = {
  labor: "劳动合同",
  service: "商事合同",
};

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={`risk ${level}`}>{RISK_LABEL[level]}</span>;
}

export default function App() {
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await fetchReviews();
        if (cancelled) return;
        setReviews(list);
        if (list.length > 0) {
          setSelectedId(list[0].id);
          setDetail(await fetchReview(list[0].id));
        }
      } catch (reason: unknown) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "无法连接 FastAPI");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const select = async (id: string) => {
    setSelectedId(id);
    setError("");
    try {
      setDetail(await fetchReview(id));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "加载审查详情失败");
    }
  };

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return reviews;
    return reviews.filter((review) => review.contract_title.toLowerCase().includes(keyword));
  }, [reviews, query]);

  const highRisk = reviews.filter((review) => review.overall_risk === "high").length;

  return (
    <div className="console">
      <header className="masthead">
        <div>
          <div className="kicker">LAWAGENT / CONTRACT REVIEW CONSOLE</div>
          <h1>合同审查控制台</h1>
          <p>条款风险 · 法条依据 · 审查意见书</p>
        </div>
        <div className="stats">
          <div>
            <b>{reviews.length}</b>
            <span>审查记录</span>
          </div>
          <div>
            <b>{highRisk}</b>
            <span>高风险</span>
          </div>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="workspace">
        <aside className="index">
          <div className="index-head">
            <span>案卷索引</span>
            <b>{filtered.length}</b>
          </div>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索合同名称"
            aria-label="搜索合同名称"
          />
          <div className="index-list">
            {loading && <div className="empty">加载中…</div>}
            {!loading && filtered.length === 0 && <div className="empty">暂无审查记录</div>}
            {filtered.map((review) => (
              <button
                type="button"
                className={`index-item ${selectedId === review.id ? "active" : ""}`}
                key={review.id}
                onClick={() => void select(review.id)}
              >
                <div className="index-top">
                  <RiskBadge level={review.overall_risk} />
                  <span className="score">{review.risk_score.toFixed(0)}</span>
                </div>
                <strong>{review.contract_title}</strong>
                <div className="index-meta">
                  {TYPE_LABEL[review.contract_type] ?? review.contract_type} · {review.findings_count} 项风险
                </div>
                <div className="index-time">{formatTime(review.created_at)}</div>
              </button>
            ))}
          </div>
        </aside>

        <main className="document">
          {detail ? (
            <>
              <div className="doc-head">
                <div>
                  <div className="doc-kicker">CONTRACT REVIEW</div>
                  <h2>{detail.contract_title}</h2>
                  <div className="doc-meta">
                    {TYPE_LABEL[detail.contract_type] ?? detail.contract_type} · 编号 {detail.id} ·{" "}
                    {formatTime(detail.created_at)}
                  </div>
                </div>
                <div className="doc-risk">
                  <div className={`risk-score ${detail.overall_risk}`}>{detail.risk_score.toFixed(0)}</div>
                  <RiskBadge level={detail.overall_risk} />
                  <span className="risk-label">风险评分 / 100</span>
                </div>
              </div>

              <div className="rule" />
              <section>
                <div className="section-label">一、总体意见</div>
                <p className="summary">{detail.summary}</p>
              </section>

              <section>
                <div className="section-label">二、逐条审查意见</div>
                {detail.findings.map((finding, index) => (
                  <article className={`finding ${finding.risk_level}`} key={`${finding.rule_id}-${finding.clause_index}`}>
                    <div className="finding-head">
                      <div>
                        <span className="clause-no">{index + 1}.</span>
                        <strong>{finding.clause_title}</strong>
                      </div>
                      <RiskBadge level={finding.risk_level} />
                    </div>
                    <p className="issue">{finding.issue}</p>
                    <div className="suggestion">修改建议：{finding.suggestion}</div>
                    {finding.legal_basis.length > 0 && (
                      <details className="basis">
                        <summary>法条依据（{finding.legal_basis.length}）</summary>
                        {finding.legal_basis.map((basis) => (
                          <div className="basis-item" key={basis.article_id}>
                            <b>
                              《{basis.law}》{basis.article}
                            </b>
                            <span>{basis.title}</span>
                            <p>{basis.text}</p>
                          </div>
                        ))}
                      </details>
                    )}
                  </article>
                ))}
                {detail.findings.length === 0 && <div className="empty">未发现明显高风险条款。</div>}
              </section>

              <details className="trace">
                <summary>审查轨迹</summary>
                {detail.trace.map((step) => (
                  <div className="trace-step" key={`${step.node}-${step.duration_ms}`}>
                    <b>{step.node}</b>
                    <span>{step.summary}</span>
                    <i>{step.duration_ms} ms</i>
                  </div>
                ))}
              </details>

              <a className="download" href={`/reviews/${detail.id}/report`} target="_blank" rel="noreferrer">
                下载审查意见书（Markdown）
              </a>
            </>
          ) : (
            <div className="empty document-empty">
              <b>选择一份合同审查记录</b>
              左侧案卷索引会列出最近的审查结果。
            </div>
          )}
        </main>
      </div>

      <footer>LawAgent · Python RAG + TypeScript Review Console</footer>
    </div>
  );
}
