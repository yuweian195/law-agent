# 架构说明

本文档补充 README，说明 LawAgent 的检索、工作流、规则与数据模型。

## 1. 分层

```text
Streamlit UI ──┐
               ├── QAService ───── 法律问答 LangGraph ── BM25 Retriever
FastAPI ───────┤                                      ├── Compensation Calculator
               └── ReviewService ─ 合同审查 LangGraph ── Risk Rules
                                                      ├── BM25 Retriever
                                                      └── Contract Parser
```

- `services/`：业务编排、ID 生成、图调用、响应映射、持久化。
- `graph/`：LangGraph 状态与节点，不包含具体规则实现。
- `tools/`：无状态规则与计算函数，可单独测试。
- `rag/`：语料加载、分词、BM25、检索与引用对象。
- `llm/`：可选语言增强；失败自动回退到模板。

## 2. 法条检索

### 语料

`data/laws/*.jsonl`，每行一个 `LegalArticle`：

```json
{"id":"labor-19","law":"中华人民共和国劳动合同法","article":"第十九条","title":"试用期期限","text":"...","tags":["试用期","期限"]}
```

加载时按 `id` 去重，非法行跳过。

### 分词

- ASCII：连续字母数字作为一个词元；
- 中文：字符二元组（bigram），单字成段时保留单字；
- 不依赖 jieba 等分词库，保证部署轻量、行为稳定。

### BM25

- `k1=1.5`、`b=0.75`；
- IDF：`log(1 + (N - df + 0.5) / (df + 0.5))`；
- 查询词去重后逐词累计。

### 加权与返回

- 标题命中：+0.35 / 词；
- 标签命中：+0.20 / 词；
- 分数压缩：`score / (score + 2)`，落在 0–1；
- 同时返回 `coverage`（查询词覆盖率）与 `matched_terms`；
- 引用守卫使用 top-3 的 `score >= 0.35` 作为“有依据”的判断条件。

## 3. 法律问答工作流

`QAState` 字段：

| 字段 | 说明 |
|---|---|
| `question` / `context` | 用户问题与补充事实 |
| `intent` | severance / probation / non_compete / ... |
| `facts` | 工作年限、月数、月薪、解除类型、是否提前通知 |
| `citations` | 检索到的法条（含分数） |
| `calculation` | 经济补偿/赔偿金结果，可为空 |
| `conclusion` / `analysis` | 最终意见 |
| `disclaimer` | 免责声明 |

节点顺序：

1. `analyze_question`：规则意图分类 + 事实抽取；
2. `retrieve_laws`：问题 + context 作为查询，top-5；
3. `calculate`：仅在解除/补偿类问题上计算金额；
4. `compose_answer`：模板生成；若 LLM 可用则润色措辞；
5. `save_record`：写入 `qa_records`。

金额计算：

- 年限折算：`full_years + (remainder >= 6 ? 1 : remainder > 0 ? 0.5 : 0)`；
- 违法解除：`2 × N × salary`；
- 普通解除：`N × salary`；
- 未提前通知：额外 `+1 × salary`；
- 不处理社平工资三倍封顶、十二年上限与其他请求。

## 4. 合同审查工作流

`ReviewState` 字段：

| 字段 | 说明 |
|---|---|
| `parsed_contract` | 标题、当事人、条款列表 |
| `findings` | 风险项 |
| `overall_risk` / `risk_score` | 高/中/低与 0–100 风险分 |
| `summary` | 总体意见 |

节点顺序：

1. `parse_contract`：按“第 X 条 / 数字编号 / 中文序号”拆分条款；
2. `scan_rules`：规则引擎逐条扫描；
3. `retrieve_context`：校验规则附带的法条是否存在于本地库，去重后附入审查意见；
4. `assess`：汇总等级与评分，生成总体意见；
5. `save_review`：写入 `contract_reviews`。

风险评分：高风险 30/项、中风险 10/项，累计封顶 100；分数越高越危险。

## 5. 数据模型

### qa_records

| 列 | 说明 |
|---|---|
| `id` | 12 位记录编号 |
| `question` | 问题 |
| `intent` | 意图 |
| `citations_count` | 引用法条数 |
| `created_at` | 时间 |
| `payload` | 完整 JSON（结论、分析、计算、引用、trace） |

### contract_reviews

| 列 | 说明 |
|---|---|
| `id` | 审查编号 |
| `contract_title` | 合同标题 |
| `contract_type` | labor / service |
| `overall_risk` | high / medium / low |
| `risk_score` | 0–100，越高越危险 |
| `findings_count` | 风险项数量 |
| `created_at` | 时间 |
| `payload` | 完整 JSON（条款、风险项、依据、trace） |

## 6. 扩展点

- **替换检索**：实现 `LawRetriever.search()` 相同返回结构，接入向量库或混合检索。
- **扩充法条**：向 `data/laws/*.jsonl` 增加条目，无需改代码。
- **新增风险规则**：在 `app/tools/risk_rules.py` 增加函数，并在 `scan_contract()` 注册；同步补测试与标签。
- **接入真实 LLM**：配置 `.env`；LLM 只改措辞，不改分数、风险与引用。
- **替换数据库**：实现 `LawRepository` 的方法集，业务层无需改动。

## 7. 部署

- 单机：`streamlit run ui/streamlit_app.py` + `uvicorn app.main:app`。
- 容器：`docker compose up --build`，API 8000，UI 8501。
- 数据：默认 `data/law_agent.db`，生产环境建议挂载持久卷并替换为 PostgreSQL。
