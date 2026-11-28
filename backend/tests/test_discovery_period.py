"""Discovery: le anomalie restano nel periodo della domanda; messaggi chiari quando l'AI non risponde."""
from nexus.agents import llm
from nexus.discovery.core import in_period, query_period


def test_period_from_question_years():
    assert query_period("Il Piano Marshall 1947-1952 e la crescita europea") == [1947, 1952]
    assert query_period("Effetti del 1929 sulle banche") == [1929, 1929]


def test_period_from_events_only_if_narrow():
    assert query_period("Piano Marshall", [1947, 1948, 1951]) == [1947, 1951]
    assert query_period("Storia della moneta", [1259, 2022]) is None
    assert query_period("Domanda senza anni") is None


def test_anomaly_inside_or_outside_period():
    p = [1947, 1952]
    assert in_period("1948-03", p)
    assert in_period("1945–1946", p)        # tocca il margine di 2 anni
    assert not in_period("1259", p)
    assert not in_period("2022-01-01", p)
    assert in_period("", p)                 # senza anni: non si esclude


def test_http_errors_are_explained():
    m = llm._http_message(404, '{"error":{"code":"model_not_found"}}', "llama-3.3-70b-versatile")
    assert "llama-3.3-70b-versatile" in m and "Sistema → Credenziali" in m and "HTTP 404" in m
    assert "temporaneo" in llm._http_message(503, "down")
    assert "URL" in llm._http_message(404, "<html>page</html>")
