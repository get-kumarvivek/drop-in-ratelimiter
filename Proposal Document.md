Step 1: Structure the Client Proposal Document
Create a clean, professional PDF or Markdown report divided into four key sections:

Executive Summary & Challenge Statement

Acknowledge the core constraints: 2,000,000 peak RPS, 5,000 checkout capacity, and 10,000 pairs of inventory.

Frame the solution: Protecting downstream order services without degrading user trust.

Architecture & Scalability Plan

Explain how the system scales using Edge Proxies + Hierarchical Token Buckets.

Detail memory management (TTL eviction / LRU bounding) to avoid server OOM crashes.

Failure Handling Strategy

Explain the Fail-Open vs. Fail-Closed philosophy: Fail open on the rate-limiter tier to prevent cascading failures, but rely on the strict inventory database lock (10,000 limit) as the absolute business ceiling.

User Experience (UX) When Limited

Outline what users see: HTTP 429 Too Many Requests paired with a friendly virtual waiting room / queuing mechanism instead of aggressive page reloads.