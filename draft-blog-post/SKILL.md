---
name: draft-blog-post
description: Draft a technical blog post in Alex's writing style
---

# Draft a Blog Post

You're helping Alex draft a technical blog post. If the target publication
isn't clear from context or the arguments, ask which one before drafting —
tone and length can depend on it.

## Writing Style Guide

!`cat ~/Documents/version-control/ai-alex/writing-style/style-guide.md`

## Article Template

!`cat ~/Documents/version-control/ai-alex/templates/blog-post-template.md`

## Examples of Alex's Writing

!`cat ~/Documents/version-control/ai-alex/writing-style/blog-examples.md`

## Task

Draft a blog post about: $ARGUMENTS

## Process

1. **Start with the Decision Narrative Pattern:**
   - Real-world problem and context
   - Constraints making the problem complex
   - Initial intuition or naive solution
   - Why that solution fails
   - Exploration of alternatives
   - Final implementation
   - Tradeoffs and lessons learned

2. **Apply constraint-first thinking** - frame decisions around real limitations

3. **Teach through surprise** - reveal hidden complexity to justify the
   architecture

4. **Include at least one rejected approach** - show your working

5. **End with generalisable lessons** - what principles emerged?

## Validation Checklist

Before finalizing, confirm:

- [ ] Opens with a concrete production problem
- [ ] Names constraints explicitly
- [ ] Includes at least one rejected or failed solution
- [ ] Explains code narratively (no raw dumps)
- [ ] Discusses tradeoffs honestly
- [ ] Ends with generalisable lessons

## Output

Provide the full draft in markdown format, ready for review and editing.
