# Contributing

## 本地开发

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

## 提交前检查

```bash
ruff check app ui tests scripts
pytest -q
python scripts/evaluate.py
```

## 代码约定

- 检索与规则放在 `app/rag/`、`app/tools/`，工作流只负责状态流转。
- 风险规则必须可复现、可单测；新增规则同步更新 `review_labels.json`。
- LLM 只能改措辞，不得生成法条编号、风险等级或金额。
- 新增法条使用 JSONL，保持 `id` 唯一，并在 README/测试中体现来源。
- 新增接口同步更新 README、架构文档与 API 表。

## 数据与合规

仓库内合同、问题与标签均为合成数据。请勿提交真实当事人信息、身份证号、手机号、工资流水或未公开合同。

本项目不提供正式法律意见；涉及真实案件的功能变更需经过法律专业人员审核。
