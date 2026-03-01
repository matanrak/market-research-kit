---
description: Define a research brief with ICPs, competitors, and hypothesis from a rough pain point.
handoffs:
  - label: Generate Research Plan
    agent: mk.plan
    prompt: Generate query plan from the brief
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

The text the user typed after `/mk.specify` is the pain point description.

Given that pain point, do this:

1. **Run `marketkit context` from project root**: Parse the JSON output for `RESEARCH_DIR`, `BRIEF`, `TEMPLATES_DIR`. Use `BRIEF` as the write path for all subsequent steps.

2. **Load the brief template**: Read `{TEMPLATES_DIR}/brief-template.md` to understand required sections.

3. **Hybrid interview — Round 1 (structured questions)**:

   Use `AskUserQuestion` for every decision point. Present your recommendation as the first option.

   **Q1 — Ideal Customer Profiles**:
   - Analyze the pain point and propose 2-3 ICPs (max 4)
   - For each ICP, research and define:
     - Role/title, demographics, company context
     - Why they matter (purchase authority, adoption potential)
     - Pain signals (specific, observable complaints — real quotes where possible)
     - Language patterns (exact phrases they'd use online)
     - Where they hang out (platforms, communities)
     - Adjacent interests
   - Assign Priority (P1/P2/P3) and Confidence (High/Medium/Low)

   - **Display ALL ICPs** using this exact markdown format, separated by `---`:

     ```markdown
     ### ICP 1 — [Name]
     `P1` `High confidence`

     **Who:**
     [Role, age range, technical level, company context. 2-3 sentences max.]

     **Why:**
     [Why they matter for this product. 2-3 sentences max.]

     **Pain signals:**
     - "[Quoted pain signal — real words they'd say]"
     - "[Another quoted pain signal]"
     - "[Another quoted pain signal]"
     - [Observable behavior, not a quote]

     **Language:** `keyword 1` · `keyword 2` · `keyword 3` · `keyword 4` · `keyword 5` · `keyword 6`

     **Where:** `platform 1` · `platform 2` · `platform 3` · `platform 4` · `platform 5`

     **Adjacent:** interest 1 · interest 2 · interest 3 · interest 4 · interest 5

     ---
     ```

   - After displaying all ICPs, use `AskUserQuestion` with **one question per ICP** in a single call (max 4 questions). Each question asks:
     - Header: "ICP N"
     - Question: "ICP N — [Name] (P[X], [Confidence])?"
     - Options:
       - "Keep" — "Looks good, no changes"
       - "Remove" — "Drop from brief"
       - "Edit" — "I have feedback"

   - If any ICP is marked "Edit", ask the user what to change and regenerate just that ICP. Then re-confirm with another `AskUserQuestion` for the edited ICP only.
   - If any ICP is marked "Remove", drop it silently and proceed.

   **Q2 — Competitors**:
   - Research and propose known competitors with:
     - Brand name and handle(s)
     - Positioning relative to the user's product/idea
     - Switching signals to watch for
   - Display each competitor using this format:

     ```markdown
     **[Competitor Name]** · `@handle`
     [One-line positioning]. Switching signals: [what makes users leave].
     ```

   - Then use `AskUserQuestion`:
     - Options: "Looks good — proceed to hypothesis", "Edit competitors", "Add more competitors"

   **Q3 — Hypothesis**:
   - Draft a clear hypothesis statement based on the pain point and ICPs
   - This should be falsifiable through the research
   - Display as:

     ```markdown
     **Hypothesis:**
     [One clear falsifiable statement]

     **We'll know this is true if:** [observable evidence from research]
     **We'll know this is false if:** [observable counter-evidence]
     ```

   - Use `AskUserQuestion`:
     - Options: "Looks good — show full brief", "Refine hypothesis"

4. **Round 2 (final review)**:
   - Show the complete brief assembled from all answers
   - Use `AskUserQuestion`:
     - Options: "Save and finish", "I have edits", "Start over"
   - If user selects edits, ask what to change. Maximum 2 refinement rounds.

5. **Save**: Write the final brief to `{BRIEF}`.

6. **Self-validation**: Re-read the saved brief. Verify all required sections (ICPs, competitors, hypothesis) are present and non-empty. If any are missing, fix them before declaring done.

7. **Report**: Show path to saved brief. Suggest running `/mk.plan` next.

## Behavior Rules

- Use `AskUserQuestion` for every confirmation or decision — never ask freeform "what do you think?"
- Always lead with your recommendation as the first option
- For ICP confirmation: use one question per ICP in a single `AskUserQuestion` call — this shows all ICPs as checkboxes the user can review at once
- Update brief.md after each confirmed answer (atomic saves)
- If user says "done" or "good enough" at any point, save and stop
- Present Q1, Q2, Q3 sequentially — wait for confirmation before moving to next
- If user has not confirmed after 2 iterations of the same question, accept the agent's recommendation and proceed
- Maximum 5 exchanges total (3 structured + up to 2 refinement rounds)
- Focus on **what people say and where** — this drives the query plan
- Use markdown formatting that renders well in Claude Code:
  - `###` for ICP headers
  - `backtick` tags with ` · ` separators for keywords, platforms
  - Plain `- "quoted"` lists for pain signals (no italics, no blockquotes)
  - `**Bold:**` labels with a newline before the content for Who/Why
