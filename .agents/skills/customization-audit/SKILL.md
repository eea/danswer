---
name: customization-audit
description: Generates a mapping of fork customizations with explicit re-implementation instructions.
---

# Customization Audit Workflow
1. **Tag Parsing**: Extract `{upstream_tag}` from `{current_tag}`.
2. **Data Extraction**: Capture full `git log` and `git diff` into `.agents/audit_logs/`.
3. **Intent & Logic Analysis**:
   - For every major change, **Claude 4.6 Sonnet** must write a "Functional Spec."
   - **Spec format**: 
     - *Goal*: What does this change achieve?
     - *Logic*: What is the specific algorithm or condition?
     - *Dependencies*: Which other custom or upstream files does this rely on?
4. **Output Generation**:
   - Create `customization_map.md`.
   - **Section IV: Re-implementation Guide**: Write a step-by-step technical instruction for *re-creating* the feature if the original files are missing or heavily refactored in the new upstream.

# Technical Guardrails
- Identify and flag "Sticky Logic": Code that must remain identical regardless of upstream changes (e.g., proprietary encryption or specific API keys).
- Track author names for each spec to allow the agent to say "This was [Author]'s logic for X."