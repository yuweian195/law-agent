# Changelog

## [0.1.0] - 2026-11-14

### Added

- 本地法条库：33 条劳动法、劳动合同法、社会保险法、民法典合同编条文。
- BM25 法条检索：中文二元组分词、标题/标签加权、相关度与覆盖率。
- 法律问答 LangGraph：意图识别、事实抽取、法条检索、金额计算、意见生成。
- 合同审查 LangGraph：条款拆分、12 条风险规则、法条依据补充、风险评分。
- 经济补偿/赔偿金计算器：N、2N、N+1。
- FastAPI 接口：法条检索、法律问答、合同审查、上传审查、Markdown 报告。
- Streamlit 法律意见书风格工作台：法律意见、合同审查、法条索引、案卷记录。
- SQLite 持久化：咨询记录与审查记录。
- 24 个单元/接口测试。
- 离线评估：检索 Recall@3、MRR、规则 Precision/Recall、问答意图/引用/金额准确率。
- 查询同义扩展：辞退/开除/劝退/被优化/N+1 等口语映射到法条术语，Recall@3 从 93% 提升到 100%。
- TypeScript + React 合同审查控制台（Vite 构建，FastAPI `/console` 静态挂载）。
- Docker Compose、GitHub Actions CI、架构文档与截图。
