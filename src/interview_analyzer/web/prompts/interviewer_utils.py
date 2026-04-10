"""Difficulty blocks, role expectations, and domain topic hints for the interviewer."""

DIFFICULTY_BLOCKS = {
    "easy": """\
DIFFICULTY CALIBRATION — EASY:
- Ask foundational questions that test understanding of core concepts.
- Accept high-level answers — do not aggressively probe for implementation details.
- Give generous hints if the candidate is stuck.
- Follow-ups are gentle extensions: "And what would happen if..." rather than \
"But what about the edge case where..."
- The goal is to assess baseline competence and communication, not to stress-test.""",

    "medium": """\
DIFFICULTY CALIBRATION — MEDIUM:
- Ask questions that require both conceptual understanding and practical experience.
- Expect candidates to discuss trade-offs and alternatives without being prompted.
- Give one hint if stuck, but expect them to run with it.
- Follow-ups should probe for depth: "How would that scale?" "What are the failure modes?"
- Push back once on weak answers: "I'm not sure that would work because of X — \
how would you handle that?\"""",

    "hard": """\
DIFFICULTY CALIBRATION — HARD:
- Ask questions that require deep expertise, novel problem-solving, and system-level thinking.
- Expect candidates to identify constraints, edge cases, and failure modes unprompted.
- Minimal hints. If stuck, redirect to a new angle rather than helping.
- Aggressive follow-ups: challenge assumptions, introduce constraints mid-answer, ask \
"what breaks."
- Push back on every answer at least once: "That's one approach, but what concerns would \
you have about it at scale?"
- Expect them to defend their choices with evidence and reasoning.""",
}


ROLE_EXPECTATIONS = {
    "Junior (0-2y)": (
        "Focus on fundamentals, basic problem solving, and learning ability. "
        "Do not ask system design questions requiring production experience."
    ),
    "Mid (2-5y)": (
        "Expect working knowledge of common patterns, ability to discuss trade-offs "
        "at a component level, and some production experience."
    ),
    "Senior (5-8y)": (
        "Expect deep technical expertise, system-level thinking, clear articulation "
        "of trade-offs, and ability to drive technical decisions."
    ),
    "Staff/Principal (8+y)": (
        "Expect cross-system architectural thinking, organizational impact awareness, "
        "ability to identify unstated requirements, and mentorship/leadership signals."
    ),
}


DOMAIN_HINTS = {
    "System Design": (
        "load balancing, caching, database selection, message queues, consistency models, "
        "API design, monitoring, scaling strategies, failure modes, CDN/edge computing"
    ),
    "Agentic AI": (
        "agent architectures (ReAct, Plan-and-Execute), tool use, memory systems, "
        "multi-agent coordination, error recovery, safety/guardrails, evaluation, "
        "LLM routing, human-in-the-loop"
    ),
    "RAG & Information Retrieval": (
        "chunking strategies, embedding models, vector databases, retrieval strategies "
        "(hybrid search, re-ranking), evaluation (recall@k, MRR), hallucination mitigation, "
        "query understanding, document processing pipelines"
    ),
    "LLM Engineering": (
        "prompt engineering, fine-tuning (LoRA, QLoRA), inference optimization "
        "(quantization, batching, KV cache), evaluation, guardrails, token economics, "
        "model selection, deployment (vLLM, TGI)"
    ),
    "Data Structures & Algorithms": (
        "arrays/strings, trees/graphs, dynamic programming, greedy algorithms, "
        "BFS/DFS, sorting/searching, hash maps, stacks/queues, sliding window, "
        "two pointers, complexity analysis"
    ),
    "Backend Engineering": (
        "API design (REST/gRPC), database design (SQL/NoSQL), authentication/authorization, "
        "caching strategies, message queues, microservices, observability, CI/CD, "
        "containerization, performance tuning"
    ),
}


TOPIC_COUNTS = {30: 3, 45: 4, 60: 5, 90: 7}
