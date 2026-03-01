---
description: Synthesize research findings into a ranked pain-point report and competitive intelligence.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). If a plan name is provided (e.g., `20260301-1430-ai-travel`), synthesize only that plan. Otherwise, synthesize all plans.

## Outline

1. **Run `marketkit context` from project root**: Parse JSON for `PROJECT_ROOT`, `RESEARCH_DIR`, `BRIEF`, `AVAILABLE_DOCS`, `PLAN_COUNT`.

2. **Gate check**: If `brief.md` is not in `AVAILABLE_DOCS`, stop: "No brief found. Run `/mk.specify` first." If `PLAN_COUNT` is 0, stop: "No research plans found. Run `/mk.research` first."

3. **Load context**:
   - Read `{BRIEF}` (ICPs, competitors, hypothesis)
   - Run `marketkit gather` (or `marketkit gather --plan {PLAN_NAME}` if specified) to get merged, deduplicated posts as JSON
   - Read existing `.market-research/report.md` if it exists (for accumulation)

4. **Select report sections**: Use `AskUserQuestion` with `multiSelect: true`:
   - Header: "Sections"
   - Question: "Which report sections should we generate?"
   - Options:
     - "Pain point ranking (Recommended)" — "Clustered pain themes ranked by frequency with evidence"
     - "Competitive intelligence" — "Competitor sentiment, switching signals, opportunities"
     - "ICP validation" — "Confidence adjustments based on actual signal data"
     - "Hypothesis check" — "Does the data support or contradict the hypothesis?"

5. **Select output format**: Use `AskUserQuestion`:
   - Header: "Format"
   - Question: "How should the report be formatted?"
   - Options:
     - "Full markdown report (Recommended)" — "Save to .market-research/report.md with all sections"
     - "Executive summary" — "Top 3 pain points + key competitive insights only"
     - "Data tables" — "Structured tables for spreadsheet export"

6. **Aggregate stats**:
   - Total post count and breakdown by angle
   - Post count per target ICP (what we searched for)

7. **Classify ICPs** (analysis pass):
   - For each post, read the content and classify which ICP the author actually belongs to
   - A post found via a "DevOps Engineer" targeted search might actually be from a solo developer
   - Use ICP definitions from brief.md (pain signals, language patterns) to classify
   - Tag each post with the determined ICP, noting when it differs from the target ICP

8. **Generate synthesis** (based on selected sections):

   ### Pain Point Report
   - Group posts by pain theme (cluster similar complaints)
   - Rank pain points by frequency (number of posts mentioning it)
   - For each pain point:
     - Summary of the pain (1-2 sentences)
     - Frequency count
     - Representative tweets (top 3-5 by engagement, with links)
     - Which ICPs experience this pain (classified, not targeted)
     - Severity signal (engagement levels, emotional language)

   ### Competitive Intelligence
   - Group competitor mentions by sentiment (positive/negative/neutral)
   - Identify switching signals (people leaving competitors)
   - Identify competitor complaints (= your opportunities)
   - For each competitor:
     - Overall sentiment summary
     - Key complaints (with tweet evidence)
     - Switching triggers (what makes people leave)
     - What they praise (what you need to match)

   ### ICP Validation
   - Which ICPs had the most signal? Adjust confidence levels.
   - Any new ICPs discovered that weren't in the brief?
   - Language pattern validation — did the predicted phrases actually appear?
   - How often did the classified ICP differ from the target ICP?
   - Recommend brief.md updates if needed.

   ### Hypothesis Check
   - Does the data support or contradict the hypothesis from brief.md?
   - What evidence supports it? What contradicts it?
   - Recommended hypothesis refinement.

9. **Display report to the user BEFORE saving**: You MUST print the report content so the user can read it before deciding to save.

   - If the report is **≤100 lines**: print the full report as formatted markdown.
   - If the report is **>100 lines**: print a summary version — top 3 pain points (with best evidence for each), key competitive insight, hypothesis verdict, and ICP confidence table. End with: `"Full report is [N] lines. Saving will include all sections."`

   Use formatted markdown:
   - Pain points as **bold headers** with `backtick` counts
   - Evidence as *italic quoted tweets*
   - ICP tags as `backtick labels`
   - Competitor sentiment as color words: "positive", "negative", "mixed"

10. **Confirm and save**: Use `AskUserQuestion`:
    - Question: "Save this report?"
    - Options: "Save report (Recommended)" — "Write to .market-research/report.md", "Refine — adjust sections or depth", "Save and update brief" — "Also update ICP confidence levels in brief.md"

11. **Write report**: Save to `.market-research/report.md`

12. **Update research history**: Append a row to the Research History table in `.market-research/brief.md`.

13. **Report**: Display synthesis summary. Highlight top 3 pain points and strongest competitive opportunities.

## Report Format

```markdown
# Market Research Report: [Pain Point Title]

**Generated**: [DATE]
**Plans analyzed**: [N]
**Total posts**: [N] (deduplicated)
**Cost to date**: ~$[X.XX]

## Top Pain Points

### 1. [Pain Point Name] (N mentions)

[Summary]

**Evidence**:
> "[tweet text]" — @author (N likes) [link]
> "[tweet text]" — @author (N likes) [link]

**ICPs affected**: `ICP 1` `ICP 2`

---

### 2. [Pain Point Name] (N mentions)
[Same structure]

---

## Competitive Intelligence

### [Competitor Name]
**Sentiment**: [Positive/Negative/Mixed]
**Switching signals**: N posts

Key complaints:
- [complaint] (N mentions)
- [complaint] (N mentions)

---

## ICP Validation

| ICP | Target Signal | Classified Signal | Confidence Update |
|-----|--------------|-------------------|-------------------|
| [Name] | [count targeted] | [count classified] | High → [adjusted] |

## Hypothesis Check

**Original**: [from brief.md]
**Verdict**: [Supported / Partially supported / Not supported]
**Evidence**: [summary]
**Refined hypothesis**: [updated statement if needed]
```

## Behavior Rules

- Use `AskUserQuestion` for section selection, format choice, and save confirmation
- Always put your recommended option first with "(Recommended)" in the label
- Display the report in formatted markdown before saving
- Use `backtick` tags for ICP names, pain point counts, and keywords throughout
