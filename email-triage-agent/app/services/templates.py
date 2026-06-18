"""
Prompt templates for the Smart Email Classifier & Rewriter service.

Design philosophy
------------------
Every prompt here follows the same four-part structure on purpose:

    1. ROLE       - tells the model what kind of expert to act as, which
                    narrows its behavior before it even sees the task.
    2. TASK       - a single, unambiguous instruction (no compound asks).
    3. CONSTRAINTS- explicit rules about output format, allowed values,
                    and edge cases, so the response is machine-parseable.
    4. OUTPUT SPEC- the exact shape of the response we expect back
                    (e.g. "respond with only one word"), which lets the
                    FastAPI layer parse the result without fragile regex.

Keeping prompts here (instead of inline in route handlers) makes the
reasoning behind each prompt easy to review, version, and unit test
independently of the API layer.
"""

from typing import Final

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------
#
# Why this design:
# - The category list is enumerated TWICE: once as a definition (with a one
#   line description of what belongs in each bucket) and once as the strict
#   output contract. Models are noticeably more accurate at classification
#   when given short positive examples of *intent* per category, not just
#   a bare label list.
# - We explicitly forbid explanations in the output. Without this
#   constraint, LLMs tend to "helpfully" add reasoning text, which breaks
#   downstream parsing.
# - We ask for the single category word in a fixed casing so the API layer
#   can validate against an enum without fuzzy matching.

CLASSIFICATION_CATEGORIES: Final[list[str]] = ["Work", "Personal", "Finance", "Spam"]

CLASSIFICATION_SYSTEM_PROMPT: Final[str] = """You are an expert email triage assistant used inside an inbox automation \
system. Your only job is to read one email and assign it to exactly one \
category. You are precise, consistent, and never add commentary."""

CLASSIFICATION_PROMPT_TEMPLATE: Final[str] = """\
TASK
Classify the email below into exactly one of these four categories.

CATEGORY DEFINITIONS
- Work: Professional correspondence, internal company communication, \
client/vendor emails, meeting requests, project updates, job-related tasks.
- Personal: Messages from friends or family, personal plans, social \
invitations, non-business personal matters.
- Finance: Bank statements, invoices, payment receipts, billing alerts, \
investment or tax-related communication, subscription charges.
- Spam: Unsolicited bulk email, phishing attempts, scams, irrelevant \
marketing with no prior relationship, suspicious links or requests.

EMAIL TO CLASSIFY
\"\"\"
{email_content}
\"\"\"

CONSTRAINTS
- Choose exactly one category from: Work, Personal, Finance, Spam.
- Base your decision on the dominant intent of the email, not isolated \
keywords (e.g. an email mentioning "invoice" in a casual aside between \
coworkers is still Work, not Finance, if the core purpose is a work update).
- If the email shows multiple signals of unsolicited bulk content, \
deceptive urgency, or requests for sensitive credentials/payments from an \
unknown sender, classify it as Spam even if it superficially resembles \
another category.

OUTPUT FORMAT
Respond with ONLY the category name, exactly as spelled above. \
No punctuation, no explanation, no extra words.
"""


def build_classification_prompt(email_content: str) -> str:
    """Build the user-turn prompt for the classification task."""
    return CLASSIFICATION_PROMPT_TEMPLATE.format(email_content=email_content.strip())


# ---------------------------------------------------------------------------
# Rewriting prompt
# ---------------------------------------------------------------------------
#
# Why this design:
# - We separate "tone" as a free-text parameter rather than a hardcoded
#   enum, since the spec says "e.g. professional, friendly" - implying the
#   set is open-ended. To keep quality high for arbitrary tones, the prompt
#   gives the model a generic *process* (preserve meaning -> adjust
#   register -> tighten phrasing) rather than tone-specific rules, so it
#   generalizes to tones we didn't anticipate (e.g. "apologetic", "urgent",
#   "casual").
# - We explicitly instruct it to preserve factual content (dates, names,
#   numbers, asks) because tone rewriting is the failure mode where models
#   most often drop or hallucinate details.
# - We ask for plain rewritten text only, no preamble like "Here's your
#   rewritten email:", which again keeps the API response clean.

REWRITE_SYSTEM_PROMPT: Final[str] = """You are an expert editor who rewrites emails to match a requested tone \
while perfectly preserving the original meaning, facts, and intent. You \
never invent new information and you never add meta-commentary about \
your edits."""

REWRITE_PROMPT_TEMPLATE: Final[str] = """\
TASK
Rewrite the email below so that it reads in a "{tone}" tone.

ORIGINAL EMAIL
\"\"\"
{email_content}
\"\"\"

PROCESS
1. Identify every factual detail in the original (names, dates, numbers, \
deadlines, action items, links) and keep all of them unchanged.
2. Identify the core intent of the email (e.g. requesting something, \
informing, apologizing, following up) and preserve that intent exactly.
3. Adjust word choice, sentence structure, and greeting/sign-off to match \
the "{tone}" tone.
4. Keep the rewritten email a similar length to the original unless the \
tone naturally requires brevity or elaboration (e.g. "concise" should \
shorten it; "formal" may lengthen it slightly).

CONSTRAINTS
- Do not add new requests, facts, or commitments that were not in the \
original email.
- Do not remove any action item, question, or deadline present in the \
original.
- If the original has no greeting or sign-off, you may add a minimal one \
appropriate to the tone, but do not invent a sender or recipient name \
that wasn't already present.

OUTPUT FORMAT
Respond with ONLY the rewritten email text. No preamble, no labels like \
"Rewritten email:", no explanation of what you changed.
"""


def build_rewrite_prompt(email_content: str, tone: str) -> str:
    """Build the user-turn prompt for the rewriting task."""
    return REWRITE_PROMPT_TEMPLATE.format(
        email_content=email_content.strip(), tone=tone.strip().lower()
    )