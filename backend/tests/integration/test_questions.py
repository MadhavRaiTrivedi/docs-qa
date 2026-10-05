import json

import httpx
import pytest
from fastapi import status

from docs_qa.dependencies import get_answer_generator
from tests.fakes import ScriptedAnswerGenerator
from tests.integration.conftest import drain
from tests.integration.sample_documents import EXPENSE_POLICY, LEAVE_POLICY
from tests.integration.test_library import create_collection, upload

pytestmark = pytest.mark.integration


async def handbook(client: httpx.AsyncClient, worker) -> str:
    collection_id = await create_collection(client)
    await upload(client, collection_id, "leave.md", LEAVE_POLICY)
    await upload(client, collection_id, "expenses.md", EXPENSE_POLICY)
    await drain(worker)
    return collection_id


async def test_search_ranks_the_matching_section_first(client, worker) -> None:
    collection_id = await handbook(client, worker)

    response = await client.post(
        f"/api/collections/{collection_id}/search",
        json={"query": "How many days of sick leave do employees get?"},
    )

    top = response.json()["hits"][0]
    assert top["fileName"] == "leave.md"
    assert top["headingPath"] == ["Leave policy", "Sick leave"]
    assert top["vectorRank"] is not None
    assert top["keywordRank"] is not None


async def test_answer_cites_the_sources_it_used(client, worker, answer_generator) -> None:
    collection_id = await handbook(client, worker)

    response = await client.post(
        f"/api/collections/{collection_id}/questions",
        json={"question": "How many days of sick leave do employees get?"},
    )

    body = response.json()
    assert body["outcome"] == "ANSWERED"
    assert [s["number"] for s in body["sources"] if s["isCited"]] == [1]
    assert body["model"] == ScriptedAnswerGenerator.model
    assert body["inputTokens"] == 100
    [(_, sources)] = answer_generator.calls
    assert sources[0].file_name == "leave.md"


async def test_answer_without_citations_is_marked_unsupported(app, client, worker) -> None:
    collection_id = await handbook(client, worker)
    app.dependency_overrides[get_answer_generator] = lambda: ScriptedAnswerGenerator(
        "I think it is about a week."
    )

    response = await client.post(
        f"/api/collections/{collection_id}/questions",
        json={"question": "How many days of sick leave do employees get?"},
    )

    assert response.json()["outcome"] == "UNSUPPORTED"


async def test_unrelated_question_is_answered_without_the_model(
    client, worker, answer_generator
) -> None:
    collection_id = await handbook(client, worker)

    response = await client.post(
        f"/api/collections/{collection_id}/questions",
        json={"question": "Which quantum chromodynamics lattice gauge?"},
    )

    assert response.json()["outcome"] == "NOT_IN_DOCUMENTS"
    assert answer_generator.calls == []


async def test_streaming_sends_sources_then_text_then_the_saved_question(client, worker) -> None:
    collection_id = await handbook(client, worker)

    async with client.stream(
        "POST",
        f"/api/collections/{collection_id}/questions/stream",
        json={"question": "How many days of sick leave do employees get?"},
    ) as response:
        events = _parse_events(await response.aread())

    names = [name for name, _ in events]
    assert names[0] == "sources"
    assert set(names[1:-1]) == {"delta"}
    assert names[-1] == "done"
    saved = (await client.get(f"/api/questions/{events[-1][1]['id']}")).json()
    assert saved["answer"].startswith("Staff get twelve days")


async def test_feedback_is_stored_with_the_question(client, worker) -> None:
    collection_id = await handbook(client, worker)
    asked = await client.post(
        f"/api/collections/{collection_id}/questions",
        json={"question": "How many days of sick leave do employees get?"},
    )
    question_id = asked.json()["id"]

    await client.put(f"/api/questions/{question_id}/feedback", json={"rating": "NOT_HELPFUL"})
    rated = await client.put(
        f"/api/questions/{question_id}/feedback", json={"rating": "HELPFUL", "comment": "Exact."}
    )
    question = (await client.get(f"/api/questions/{question_id}")).json()

    assert rated.status_code == status.HTTP_200_OK
    assert question["feedback"]["rating"] == "HELPFUL"
    assert question["feedback"]["comment"] == "Exact."


async def test_questions_without_a_configured_model_return_503(app, client, worker) -> None:
    collection_id = await handbook(client, worker)
    del app.dependency_overrides[get_answer_generator]

    response = await client.post(
        f"/api/collections/{collection_id}/questions", json={"question": "Sick leave?"}
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def _parse_events(body: bytes) -> list[tuple[str, object]]:
    events = []
    for block in body.decode().strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        events.append(
            (name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: ")))
        )
    return events
