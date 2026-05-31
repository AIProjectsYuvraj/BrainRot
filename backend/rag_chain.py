import random

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

from backend.models import BrainRotResponse
from backend.personalities import BONUS_INSTRUCTIONS, NO_CONTEXT_MESSAGES, PERSONALITIES
from backend.vectorstore import get_retriever


class BrainRotState(MessagesState):
    personality: str
    retrieved_context: str
    bonus_instruction: str
    bonus_type: str
    sources: list[str]
    brainrot_response: BrainRotResponse | None


def _get_last_human_message(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
        if isinstance(msg, dict) and msg.get("type") == "human":
            return msg["content"]
    return ""


def retrieve_node(state: BrainRotState) -> dict:
    question = _get_last_human_message(state["messages"])
    retriever = get_retriever(k=4)
    docs = retriever.invoke(question)

    if not docs:
        return {"retrieved_context": "", "sources": []}

    context_parts = []
    sources: list[str] = []
    seen_sources: set[str] = set()
    for i, doc in enumerate(docs, 1):
        context_parts.append(f"[Chunk {i}]\n{doc.page_content}")
        source = doc.metadata.get("source", "unknown")
        if source not in seen_sources:
            seen_sources.add(source)
            sources.append(source)

    return {
        "retrieved_context": "\n\n".join(context_parts),
        "sources": sources,
    }


def agent_node(state: BrainRotState) -> dict:
    personality = state["personality"]
    bonus_instruction = state["bonus_instruction"]
    bonus_type = state["bonus_type"]
    retrieved_context = state.get("retrieved_context", "")
    sources = state.get("sources", [])

    if not retrieved_context:
        response = BrainRotResponse(
            answer=NO_CONTEXT_MESSAGES.get(personality, NO_CONTEXT_MESSAGES["tired"]),
            bonus_type=bonus_type,
            bonus_content="Feed me something first — URL, PDF, or raw text.",
            sources=[],
        )
        return {
            "brainrot_response": response,
            "messages": [AIMessage(content=response.answer)],
        }

    system_content = f"""{PERSONALITIES[personality]}

## Retrieved Context
{retrieved_context}

## Bonus Instruction
{bonus_instruction}

## Structured Output Requirements
- answer: Your main response in character. Do NOT include the bonus content here.
- bonus_type: Must be exactly "{bonus_type}".
- bonus_content: The bonus content only (without the label prefix).
- sources: List of source URLs or filenames you used from the context."""

    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    structured_llm = llm.with_structured_output(BrainRotResponse)

    messages = [SystemMessage(content=system_content)] + list(state["messages"])
    response: BrainRotResponse = structured_llm.invoke(messages)

    if not response.sources and sources:
        response = BrainRotResponse(
            answer=response.answer,
            bonus_type=response.bonus_type,
            bonus_content=response.bonus_content,
            sources=sources,
        )

    return {
        "brainrot_response": response,
        "messages": [AIMessage(content=response.answer)],
    }


def _build_graph():
    graph = StateGraph(BrainRotState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("agent", agent_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "agent")
    graph.add_edge("agent", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def select_bonus() -> tuple[str, str]:
    return random.choice(BONUS_INSTRUCTIONS)


def chat(question: str, personality: str, session_id: str) -> BrainRotResponse:
    bonus_type, bonus_instruction = select_bonus()
    graph = get_graph()

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=question)],
            "personality": personality,
            "bonus_instruction": bonus_instruction,
            "bonus_type": bonus_type,
            "retrieved_context": "",
            "sources": [],
            "brainrot_response": None,
        },
        config={"configurable": {"thread_id": session_id}},
    )

    return result["brainrot_response"]
