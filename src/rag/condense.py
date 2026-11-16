from rag.core.config import GROQ_CONDENSE_MODEL, get_groq_client
from rag.core.prompts import condense_prompt, summary_prompt

# ==============================================================================
# Condnse history and mamke clean quary
# ==============================================================================


def condense_history(
    query: str,
    messages: list[dict] | None = None,
    summary: str = "",
) -> str:
    """
    Rewrites a follow-up question into a standalone search query.

    Args:
        query: The latest user question (e.g. "Give me examples of it").
        messages: List of standard chat messages [{"role": "user", "content": "..."}, ...].
        summary: Optional running summary of older turns stored in DB.
    """

    # Normalize histoy lines
    clean_query = query.strip()

    if not messages and not summary:
        return clean_query

    history_lines = []
    if summary:
        history_lines.append(f"Summary: {summary.strip()}")

    for msg in messages or []:
        role = msg.get("role", "User").capitalize()
        content = msg.get("content", "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    if not history_lines:
        return clean_query

    # Build Prompt
    prompt = (
        condense_prompt()
        .replace("{chat_history}", "\n".join(history_lines))
        .replace("{query_str}", clean_query)
    )

    # Call Groq with graceful fallback
    try:
        groq = get_groq_client()
        response = groq.chat.completions.create(
            model=GROQ_CONDENSE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        rewritten = response.choices[0].message.content.strip().strip("\"'")
        return rewritten or clean_query
    except Exception as e:
        print(f"Condense query failed ({e}), using original query.")
        return clean_query


# ==============================================================================
# Create summary
# ==============================================================================


def update_summary(
    old_messages: list[dict],
    current_summary: str = "",
) -> str:
    if not old_messages:
        return current_summary

    # Format the messages to be summarized
    text_chat = "\n".join(
        f"{m.get('role', 'User').capitalize()}: {m.get('content', '')}"
        for m in old_messages
    )

    prompt = (
        summary_prompt()
        .replace("{current_summary}", current_summary or "None")
        .replace("{chat_text}", text_chat)
    )

    try:
        groq = get_groq_client()
        response = groq.chat.completions.create(
            model=GROQ_CONDENSE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Summary update failed ({e}), keeping current summary.")
        return current_summary
