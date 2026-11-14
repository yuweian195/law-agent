"""LawAgent document-style workbench.

Run from the repository root:
    streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import (  # noqa: E402
    ContractReview,
    ContractReviewRequest,
    LawSearchResponse,
    QARecord,
    QARequest,
    RiskLevel,
)
from app.services.law import get_law_service  # noqa: E402
from app.services.qa import get_qa_service  # noqa: E402
from app.services.reporting import qa_markdown, review_markdown  # noqa: E402
from app.services.review import get_review_service  # noqa: E402
from app.tools.contract_parser import decode_text  # noqa: E402

st.set_page_config(
    page_title="LawAgent · 法律意见与合同审查",
    page_icon="§",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  [data-testid="stSidebar"] { display: none; }
  [data-testid="stHeader"] { background: #f3eee2; }
  [data-testid="stToolbar"] { visibility: hidden; height: 0; }
  .stApp { background: #f3eee2; color: #1f2a37; }
  .block-container { max-width: 1320px; padding-top: 2.2rem; padding-bottom: 3rem; }
  h1, h2, h3 { font-family: Georgia, "Times New Roman", "Songti SC", "SimSun", serif; }

  .lex-masthead {
    display: flex; justify-content: space-between; align-items: flex-end; gap: 24px;
    border-top: 4px solid #7f1d1d; border-bottom: 1px solid #c9bda3;
    padding: 14px 0 12px; margin-bottom: 6px;
  }
  .lex-kicker { font-size: .68rem; letter-spacing: .24em; color: #8a6a2f; text-transform: uppercase; }
  .lex-brand {
    font-family: Georgia, "Times New Roman", "Songti SC", serif;
    font-size: 2.05rem; font-weight: 700; color: #1f2a37; letter-spacing: .02em; line-height: 1.15;
  }
  .lex-brand b { color: #7f1d1d; font-weight: 700; }
  .lex-status { font-size: .76rem; color: #6b5a3a; text-align: right; line-height: 1.8; }
  .lex-status code { background: #e9e0cc; color: #4b3b1f; padding: 2px 6px; border-radius: 3px; }
  .lex-nav-note { font-size: .7rem; color: #8a6a2f; letter-spacing: .14em; text-transform: uppercase; margin: 2px 0 0; }

  div[role="radiogroup"] { flex-direction: row; gap: 4px; border-bottom: 1px solid #c9bda3; padding-bottom: 2px; margin-bottom: 18px; }
  div[role="radiogroup"] label { padding: 4px 12px; }
  div[role="radiogroup"] label p { font-family: Georgia, "Songti SC", serif; font-size: .92rem; }
  div[role="radiogroup"] label:has(input:checked) { border-bottom: 2px solid #7f1d1d; }

  .lex-paper {
    background: #fffdf7; border: 1px solid #d8cdb4; padding: 26px 30px;
    box-shadow: 3px 3px 0 #e6dcc6;
  }
  .lex-paper + .lex-paper { margin-top: 16px; }
  .lex-doc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
  .lex-doc-title {
    font-family: Georgia, "Songti SC", serif; font-size: 1.55rem; font-weight: 700;
    color: #1f2a37; letter-spacing: .02em;
  }
  .lex-meta { font-family: "Courier New", monospace; font-size: .72rem; color: #8a6a2f; line-height: 1.8; }
  .lex-section { border-top: 1px solid #e3d8c1; margin-top: 20px; padding-top: 14px; }
  .lex-label { font-size: .68rem; letter-spacing: .2em; color: #8a6a2f; text-transform: uppercase; }
  .lex-opinion { font-family: "Songti SC", "SimSun", serif; font-size: 1rem; line-height: 2; color: #26303c; margin-top: 8px; }
  .lex-analysis { font-family: "Songti SC", "SimSun", serif; font-size: .9rem; line-height: 1.95; color: #3f4a58; margin-top: 8px; }
  .lex-calc { font-family: Georgia, serif; font-size: 2.35rem; color: #7f1d1d; line-height: 1.1; margin: 6px 0 4px; }
  .lex-calc small { font-size: .9rem; color: #8a6a2f; font-weight: 400; }
  .lex-list { font-size: .82rem; color: #4b5563; line-height: 1.9; }
  .lex-stamp {
    display: inline-block; border: 2px solid #7f1d1d; color: #7f1d1d; padding: 3px 9px;
    font-family: Georgia, serif; font-size: .72rem; font-weight: 700; letter-spacing: .12em;
    transform: rotate(-2deg); white-space: nowrap;
  }
  .lex-stamp.medium { border-color: #a16207; color: #a16207; }
  .lex-stamp.low { border-color: #166534; color: #166534; }
  .lex-disclaimer {
    margin-top: 20px; border-top: 1px solid #e3d8c1; padding-top: 12px;
    font-size: .74rem; color: #7c6f5a; line-height: 1.8;
  }
  .lex-cite { display: grid; grid-template-columns: 26px 1fr; gap: 10px; padding: 9px 0; border-bottom: 1px dotted #d8cdb4; }
  .lex-cite:last-child { border-bottom: none; }
  .lex-cite-no { font-family: Georgia, serif; color: #7f1d1d; font-weight: 700; font-size: .9rem; }
  .lex-cite-law { font-size: .73rem; color: #8a6a2f; margin-bottom: 3px; }
  .lex-cite-text { font-family: "Songti SC", "SimSun", serif; font-size: .8rem; line-height: 1.85; color: #374151; }
  .lex-summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 12px; }
  .lex-summary-cell { border-top: 2px solid #c9bda3; padding-top: 8px; }
  .lex-big { font-family: Georgia, serif; font-size: 1.55rem; color: #1f2a37; line-height: 1.2; }
  .lex-finding { border-left: 3px solid #7f1d1d; padding: 2px 0 2px 16px; margin: 20px 0; }
  .lex-finding.medium { border-left-color: #a16207; }
  .lex-finding.low { border-left-color: #166534; }
  .lex-clause { font-family: Georgia, "Songti SC", serif; font-size: 1.02rem; font-weight: 700; color: #1f2a37; }
  .lex-issue { font-family: "Songti SC", "SimSun", serif; font-size: .88rem; line-height: 1.9; color: #374151; margin-top: 6px; }
  .lex-suggest { background: #f7f1e3; border-left: 2px solid #a67c2e; padding: 8px 11px; font-size: .8rem; line-height: 1.8; color: #4b3b1f; margin-top: 8px; }
  .lex-foot { font-size: .72rem; color: #7c6f5a; line-height: 1.8; margin-top: 5px; }
  .lex-empty { border: 1px dashed #c9bda3; padding: 48px 24px; text-align: center; color: #8a7a5c; background: #fbf7ec; }
  .lex-empty b { display: block; font-family: Georgia, "Songti SC", serif; font-size: 1.1rem; color: #5b4a2c; margin-bottom: 6px; }
  .lex-law-row { border-bottom: 1px solid #e3d8c1; padding: 14px 0; }
  .lex-law-title { font-family: Georgia, "Songti SC", serif; font-size: 1rem; font-weight: 700; color: #1f2a37; }
  .lex-law-meta { font-family: "Courier New", monospace; font-size: .72rem; color: #8a6a2f; margin: 2px 0 6px; }
  .lex-law-text { font-family: "Songti SC", "SimSun", serif; font-size: .84rem; line-height: 1.9; color: #374151; }
  .lex-tag { display: inline-block; border: 1px solid #c9bda3; color: #6b5a3a; padding: 2px 7px; margin: 6px 4px 0 0; font-size: .68rem; }
  .lex-step { display: grid; grid-template-columns: 120px 1fr 58px; gap: 10px; padding: 6px 0; border-bottom: 1px dotted #d8cdb4; font-size: .75rem; }
  .lex-step b { color: #1f2a37; }
  .lex-step span { color: #6b7280; }
  .lex-step i { color: #9ca3af; font-style: normal; text-align: right; }
  .stButton > button[kind="primary"] { border-radius: 2px; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)

RISK_LABEL = {
    RiskLevel.HIGH: ("高风险", "high"),
    RiskLevel.MEDIUM: ("中风险", "medium"),
    RiskLevel.LOW: ("低风险", "low"),
}
INTENT_LABEL = {
    "severance": "解除与补偿",
    "probation": "试用期",
    "non_compete": "竞业限制",
    "service_period": "服务期",
    "social_insurance": "社会保险",
    "overtime": "加班工资",
    "contract_penalty": "违约金",
    "general": "一般咨询",
}
CONTRACT_TYPE_LABEL = {"labor": "劳动合同", "service": "商事合同"}
QA_SAMPLES = [
    ("违法解除赔偿", "公司违法解除劳动合同，我工作3年2个月，月薪2万，能拿多少赔偿？"),
    ("试用期期限", "试用期6个月合法吗？合同期1年"),
    ("竞业限制补偿", "竞业限制没有约定补偿金，还有效吗？"),
    ("社保与解除", "公司不给我交社保，我可以解除合同并要补偿吗？"),
]
CONTRACT_SAMPLES = [
    ("劳动合同（高风险）", "labor_contract_risky.txt", "labor"),
    ("劳动合同（合规）", "labor_contract_clean.txt", "labor"),
    ("技术服务合同", "service_contract.txt", "service"),
]


def load_qa_sample(question: str) -> None:
    st.session_state.qa_question = question
    st.session_state.qa_result = None


def load_contract_sample(filename: str, contract_type: str) -> None:
    path = ROOT / "data" / "contracts" / filename
    st.session_state.contract_input = path.read_text(encoding="utf-8")
    st.session_state.contract_type = contract_type
    st.session_state.review_result = None


def stamp(level: RiskLevel) -> str:
    label, css = RISK_LABEL[level]
    return f'<span class="lex-stamp {css}">{label}</span>'


def citation_html(citations, start: int = 1) -> str:
    items = []
    for index, citation in enumerate(citations, start=start):
        items.append(
            f'<div class="lex-cite"><div class="lex-cite-no">{index}</div>'
            f'<div><div class="lex-cite-law">《{html.escape(citation.law)}》'
            f'{html.escape(citation.article)} · {html.escape(citation.title)}'
            f' · 相关度 {citation.score:.0%}</div>'
            f'<div class="lex-cite-text">{html.escape(citation.text)}</div></div></div>'
        )
    return "".join(items)


def trace_html(trace) -> str:
    return "".join(
        f'<div class="lex-step"><b>{html.escape(step.node)}</b>'
        f'<span>{html.escape(step.summary)}</span><i>{step.duration_ms} ms</i></div>'
        for step in trace
    )


def render_qa_document(record: QARecord, key_prefix: str = "main") -> None:
    parts = [
        '<div class="lex-paper">',
        '<div class="lex-doc-head"><div>',
        '<div class="lex-kicker">LEGAL OPINION</div>',
        '<div class="lex-doc-title">法律意见书</div>',
        "</div><div style=\"text-align:right;\">",
        f'<div class="lex-meta">编号 {record.id}</div>',
        f'<div class="lex-meta">{record.created_at.strftime("%Y-%m-%d %H:%M")}</div>',
        f'<div class="lex-meta">事项：{html.escape(INTENT_LABEL.get(record.intent, record.intent))}</div>',
        "</div></div>",
        '<div class="lex-section"><div class="lex-label">咨询事项</div>',
        f'<div class="lex-opinion">{html.escape(record.question)}</div></div>',
        '<div class="lex-section"><div class="lex-label">一、结论</div>',
        f'<div class="lex-opinion">{html.escape(record.conclusion)}</div></div>',
        '<div class="lex-section"><div class="lex-label">二、分析</div>',
        f'<div class="lex-analysis">{html.escape(record.analysis)}</div></div>',
    ]
    if record.calculation and record.calculation.applies:
        breakdown = "".join(
            f'<div class="lex-list">· {html.escape(item)}</div>'
            for item in record.calculation.breakdown
        )
        assumptions = "".join(
            f'<div class="lex-list">· {html.escape(item)}</div>'
            for item in record.calculation.assumptions
        )
        parts += [
            '<div class="lex-section"><div class="lex-label">三、金额测算</div>',
            f'<div class="lex-calc">￥{record.calculation.amount:,.0f}<small> 元</small></div>',
            f'<div class="lex-meta">{html.escape(record.calculation.formula)}</div>',
            breakdown,
            '<div class="lex-label" style="margin-top:12px;">测算假设</div>',
            assumptions,
            "</div>",
        ]
    parts += [
        f'<div class="lex-disclaimer">{html.escape(record.disclaimer)}</div></div>',
    ]
    document_html = "".join(parts)
    left, right = st.columns([0.64, 0.36], gap="large")
    with left:
        st.markdown(document_html, unsafe_allow_html=True)
    with right:
        st.markdown(
            '<div class="lex-paper"><div class="lex-label">法条索引</div>'
            + (
                citation_html(record.citations)
                if record.citations
                else '<div class="lex-analysis">未检索到可引用的法条。</div>'
            )
            + "</div>",
            unsafe_allow_html=True,
        )
        with st.expander("查看检索与生成轨迹", expanded=False):
            st.markdown(
                f'<div class="lex-paper" style="padding:14px 16px;">{trace_html(record.trace)}</div>',
                unsafe_allow_html=True,
            )
        st.download_button(
            "下载法律意见书",
            data=qa_markdown(record),
            file_name=f"legal-opinion-{record.id}.md",
            mime="text/markdown",
            key=f"download_qa_{key_prefix}_{record.id}",
        )


def render_review_document(review: ContractReview, key_prefix: str = "main") -> None:
    high = sum(1 for item in review.findings if item.risk_level == RiskLevel.HIGH)
    medium = sum(1 for item in review.findings if item.risk_level == RiskLevel.MEDIUM)

    parts = [
        '<div class="lex-paper">',
        '<div class="lex-doc-head"><div>',
        '<div class="lex-kicker">CONTRACT REVIEW</div>',
        '<div class="lex-doc-title">合同审查意见书</div>',
        "</div><div style=\"text-align:right;\">",
        f'<div class="lex-meta">编号 {review.id}</div>',
        f'<div class="lex-meta">{review.created_at.strftime("%Y-%m-%d %H:%M")}</div>',
        f'<div class="lex-meta">{html.escape(CONTRACT_TYPE_LABEL.get(review.contract_type, review.contract_type))}</div>',
        "</div></div>",
        '<div class="lex-section"><div class="lex-label">审查对象</div>',
        f'<div class="lex-opinion">{html.escape(review.contract_title)}</div>',
        '<div class="lex-summary-grid">',
        '<div class="lex-summary-cell"><div class="lex-label">风险等级</div>',
        f'<div style="margin-top:6px;">{stamp(review.overall_risk)}</div></div>',
        '<div class="lex-summary-cell"><div class="lex-label">风险评分</div>',
        f'<div class="lex-big">{review.risk_score:.0f}'
        '<small style="font-size:.8rem;color:#8a6a2f;"> /100</small></div></div>',
        '<div class="lex-summary-cell"><div class="lex-label">风险项</div>',
        f'<div class="lex-big">{len(review.findings)}</div>'
        f'<div class="lex-meta">高 {high} · 中 {medium}</div></div>',
        '<div class="lex-summary-cell"><div class="lex-label">条款数</div>',
        f'<div class="lex-big">{len(review.clauses)}</div></div>',
        "</div></div>",
        '<div class="lex-section"><div class="lex-label">一、总体意见</div>',
        f'<div class="lex-opinion">{html.escape(review.summary)}</div></div>',
    ]

    if review.findings:
        parts.append('<div class="lex-section"><div class="lex-label">二、逐条审查意见</div>')
        for index, finding in enumerate(review.findings, start=1):
            css = RISK_LABEL[finding.risk_level][1]
            basis = "".join(
                f'<div class="lex-foot">《{html.escape(item.law)}》{html.escape(item.article)}：'
                f'{html.escape(item.text[:220])}</div>'
                for item in finding.legal_basis
            )
            parts.append(
                f'<div class="lex-finding {css}">'
                f'<div class="lex-clause">{index}. {html.escape(finding.clause_title)} '
                f'{stamp(finding.risk_level)}</div>'
                f'<div class="lex-issue">{html.escape(finding.issue)}</div>'
                f'<div class="lex-suggest">修改建议：{html.escape(finding.suggestion)}</div>'
                f"{basis}</div>"
            )
        parts.append("</div>")

    parts.append(
        '<div class="lex-disclaimer">本意见书由规则与本地法条库生成，不构成正式法律意见；'
        "签署或修改合同前，建议由执业律师结合交易背景复核。</div></div>"
    )
    st.markdown("".join(parts), unsafe_allow_html=True)

    st.download_button(
        "下载合同审查意见书",
        data=review_markdown(review),
        file_name=f"contract-review-{review.id}.md",
        mime="text/markdown",
        key=f"download_review_{key_prefix}_{review.id}",
    )

    with st.expander("查看审查轨迹", expanded=False):
        st.markdown(
            f'<div class="lex-paper" style="padding:14px 16px;">{trace_html(review.trace)}</div>',
            unsafe_allow_html=True,
        )


qa_service = get_qa_service()
review_service = get_review_service()
law_service = get_law_service()
mode = f"在线模型 · {qa_service.llm.settings.llm_model}" if qa_service.llm.enabled else "离线规则模式"

st.markdown(
    f"""
    <div class="lex-masthead">
      <div>
        <div class="lex-kicker">LAW · RETRIEVAL · REVIEW</div>
        <div class="lex-brand">Law<b>Agent</b> 法律意见工作台</div>
      </div>
      <div class="lex-status">
        本地法条库 <code>{law_service.count()}</code> 条 · BM25 检索<br/>
        运行模式：{html.escape(mode)}
      </div>
    </div>
    <div class="lex-nav-note">法条 RAG · 合同风险审查 · 金额测算</div>
    """,
    unsafe_allow_html=True,
)

page = st.radio(
    "导航",
    ["法律意见", "合同审查", "法条索引", "案卷记录"],
    horizontal=True,
    label_visibility="collapsed",
)

if page == "法律意见":
    st.markdown('<div class="lex-section" style="margin-top:4px;"><div class="lex-label">咨询事项</div>', unsafe_allow_html=True)
    if "qa_question" not in st.session_state:
        st.session_state.qa_question = QA_SAMPLES[0][1]
    sample_cols = st.columns(4)
    for index, (label, question) in enumerate(QA_SAMPLES):
        with sample_cols[index]:
            st.button(
                label,
                key=f"qa_sample_{index}",
                width="stretch",
                on_click=load_qa_sample,
                args=(question,),
            )
    question = st.text_area(
        "问题",
        key="qa_question",
        height=105,
        label_visibility="collapsed",
        placeholder="描述你的问题，例如：公司违法解除劳动合同，工作 3 年 2 个月，月薪 2 万，能拿多少赔偿？",
    )
    with st.expander("补充事实（可选）", expanded=False):
        context = st.text_area(
            "补充事实",
            key="qa_context",
            height=90,
            placeholder="合同期限、工资流水、解除通知、竞业限制约定等",
            label_visibility="collapsed",
        )
    ask = st.button("出具法律意见", type="primary", key="run_qa")
    st.markdown("</div>", unsafe_allow_html=True)

    if ask:
        if len(question.strip()) < 5:
            st.error("请输入至少 5 个字符的问题。")
        else:
            with st.spinner("检索法条并起草意见…"):
                st.session_state.qa_result = qa_service.ask(
                    QARequest(question=question, context=context)
                ).model_dump(mode="json")

    stored = st.session_state.get("qa_result")
    if stored:
        render_qa_document(QARecord.model_validate(stored))
    else:
        st.markdown(
            '<div class="lex-empty"><b>尚未提交咨询</b>'
            "选择示例或输入问题，系统会检索本地法条并出具带引用的法律意见书。</div>",
            unsafe_allow_html=True,
        )

elif page == "合同审查":
    st.markdown('<div class="lex-section" style="margin-top:4px;"><div class="lex-label">审查材料</div>', unsafe_allow_html=True)
    contract_type = st.selectbox(
        "合同类型",
        options=["labor", "service"],
        format_func=lambda value: "劳动合同" if value == "labor" else "商事合同",
        key="contract_type",
    )
    sample_cols = st.columns(3)
    for index, (label, filename, sample_type) in enumerate(CONTRACT_SAMPLES):
        with sample_cols[index]:
            st.button(
                label,
                key=f"contract_sample_{index}",
                width="stretch",
                on_click=load_contract_sample,
                args=(filename, sample_type),
            )

    if "contract_input" not in st.session_state:
        st.session_state.contract_input = (
            ROOT / "data" / "contracts" / "labor_contract_risky.txt"
        ).read_text(encoding="utf-8")

    uploaded = st.file_uploader(
        "上传合同（PDF / DOCX / TXT）",
        type=["pdf", "docx", "txt", "md"],
        key="contract_file",
    )
    uploaded_text = ""
    if uploaded is not None:
        uploaded_text = decode_text(uploaded.name, uploaded.getvalue())
        st.caption(f"已读取 {uploaded.name}，共 {len(uploaded_text)} 字符")

    contract_text = st.text_area(
        "合同文本",
        key="contract_input",
        height=250,
        label_visibility="collapsed",
    )
    review = st.button("出具审查意见", type="primary", key="run_review")
    st.markdown("</div>", unsafe_allow_html=True)

    if review:
        text = uploaded_text or contract_text
        if len(text.strip()) < 20:
            st.error("请上传合同或粘贴至少 20 个字符的合同文本。")
        else:
            with st.spinner("解析条款、扫描风险并检索法条…"):
                st.session_state.review_result = review_service.review(
                    ContractReviewRequest(contract_text=text, contract_type=contract_type)
                ).model_dump(mode="json")

    stored = st.session_state.get("review_result")
    if stored:
        render_review_document(ContractReview.model_validate(stored))
    else:
        st.markdown(
            '<div class="lex-empty"><b>尚未提交审查</b>'
            "载入示例合同或上传文件，系统会输出风险清单、修改建议和法条依据。</div>",
            unsafe_allow_html=True,
        )

elif page == "法条索引":
    st.markdown('<div class="lex-section" style="margin-top:4px;"><div class="lex-label">法条检索</div>', unsafe_allow_html=True)
    query_col, k_col = st.columns([0.8, 0.2])
    with query_col:
        law_query = st.text_input(
            "检索关键词",
            value="竞业限制 补偿",
            label_visibility="collapsed",
            placeholder="例如：试用期、竞业限制、经济补偿、违约金",
        )
    with k_col:
        top_k = st.slider("返回条数", min_value=1, max_value=10, value=5)
    if st.button("检索法条", key="run_law_search"):
        st.session_state.law_results = law_service.search(
            law_query, top_k=top_k
        ).model_dump(mode="json")
    st.markdown("</div>", unsafe_allow_html=True)

    stored_laws = st.session_state.get("law_results")
    if stored_laws:
        results = LawSearchResponse.model_validate(stored_laws)
        st.markdown('<div class="lex-paper">', unsafe_allow_html=True)
        for item in results.results:
            tags = "".join(f'<span class="lex-tag">{html.escape(tag)}</span>' for tag in item.article.tags[:6])
            st.markdown(
                f'<div class="lex-law-row">'
                f'<div class="lex-law-title">{html.escape(item.article.title)}</div>'
                f'<div class="lex-law-meta">《{html.escape(item.article.law)}》'
                f'{html.escape(item.article.article)} · 相关度 {item.score:.0%}</div>'
                f'<div class="lex-law-text">{html.escape(item.article.text)}</div>'
                f'<div>{tags}</div></div>',
                unsafe_allow_html=True,
            )
        if not results.results:
            st.markdown('<div class="lex-analysis">没有检索到相关法条，请换一个关键词。</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="lex-empty"><b>法条索引</b>输入关键词检索本地法条库；检索结果会保留在当前页面。</div>',
            unsafe_allow_html=True,
        )

else:
    qa_records = qa_service.list_recent(20)
    review_records = review_service.list_recent(20)

    if qa_records:
        st.markdown('<div class="lex-section" style="margin-top:4px;"><div class="lex-label">法律咨询案卷</div>', unsafe_allow_html=True)
        st.dataframe(
            [
                {
                    "时间": item.created_at.strftime("%m-%d %H:%M"),
                    "事项": item.question[:52],
                    "类型": INTENT_LABEL.get(item.intent, item.intent),
                    "引用": item.citations_count,
                }
                for item in qa_records
            ],
            width="stretch",
            hide_index=True,
        )
        qa_options = {
            f"{item.created_at.strftime('%m-%d %H:%M')} · {item.question[:32]}": item.id
            for item in qa_records
        }
        chosen_qa = st.selectbox("调阅咨询案卷", options=list(qa_options.keys()), key="history_qa")
        detail = qa_service.get_record(qa_options[chosen_qa])
        if detail:
            render_qa_document(detail, key_prefix="history")
        st.markdown("</div>", unsafe_allow_html=True)

    if review_records:
        st.markdown('<div class="lex-section" style="margin-top:20px;"><div class="lex-label">合同审查案卷</div>', unsafe_allow_html=True)
        st.dataframe(
            [
                {
                    "时间": item.created_at.strftime("%m-%d %H:%M"),
                    "合同": item.contract_title,
                    "等级": RISK_LABEL[item.overall_risk][0],
                    "评分": round(item.risk_score),
                    "风险项": item.findings_count,
                }
                for item in review_records
            ],
            width="stretch",
            hide_index=True,
        )
        review_options = {
            f"{item.created_at.strftime('%m-%d %H:%M')} · {item.contract_title[:32]}": item.id
            for item in review_records
        }
        chosen_review = st.selectbox(
            "调阅审查案卷", options=list(review_options.keys()), key="history_review"
        )
        detail = review_service.get_review(review_options[chosen_review])
        if detail:
            render_review_document(detail, key_prefix="history")
        st.markdown("</div>", unsafe_allow_html=True)

    if not qa_records and not review_records:
        st.markdown(
            '<div class="lex-empty"><b>暂无案卷</b>完成一次法律咨询或合同审查后，记录会自动归档。</div>',
            unsafe_allow_html=True,
        )
