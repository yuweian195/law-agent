
from app.rag.corpus import load_articles
from app.rag.retriever import LawRetriever


def test_corpus_loads_all_articles():
    articles = load_articles()
    assert len(articles) >= 30
    ids = {article.id for article in articles}
    assert "labor-19" in ids
    assert "labor-47" in ids
    assert "civil-585" in ids


def test_keyword_search_returns_expected_articles():
    retriever = LawRetriever()
    results = retriever.search("试用期最长可以多久", top_k=3)

    assert results
    assert results[0].article.id == "labor-19"
    assert results[0].score > 0


def test_retrieval_recall_and_mrr(eval_questions):
    retriever = LawRetriever()
    hits = 0
    reciprocal_ranks: list[float] = []

    for item in eval_questions:
        results = [result.article.id for result in retriever.search(item["question"], top_k=3)]
        expected = item["expected_articles"]
        if any(article_id in results for article_id in expected):
            hits += 1
        rank = next(
            (index + 1 for index, article_id in enumerate(results) if article_id in expected),
            None,
        )
        reciprocal_ranks.append(1 / rank if rank else 0.0)

    recall = hits / len(eval_questions)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    assert recall >= 0.9
    assert mrr >= 0.7


def test_law_filter():
    retriever = LawRetriever()
    results = retriever.search("违约金", top_k=10, law="民法典")

    assert results
    assert all("民法典" in item.article.law for item in results)
