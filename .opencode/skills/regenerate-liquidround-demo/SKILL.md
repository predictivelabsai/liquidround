---
name: regenerate-liquidround-demo
description: Audit LiquidRound's current routes, navigation, agents, tools, and exports against its user guide; archive prior guide/demo outputs under docs/archive; refresh the guide; and generate timestamped LiquidRound AI Platform Demo Markdown and PDF documents with a page-numbered table of contents. Use for user-guide refreshes, platform demo document regeneration, documentation deltas, or after LiquidRound functionality changes.
---

# Regenerate LiquidRound Demo

Produce documentation from the codebase rather than relying on the previous guide.

## Workflow

1. Work from the LiquidRound repository root.
2. Read repository guidance, especially `CLAUDE.md` and `SKILLS.md`.
3. Audit actual functionality:
   - Inspect `agents/registry.py` for registered agents, prefixes, categories, and descriptions.
   - Inspect `components/chat_shell.py` for current navigation.
   - Inspect route decorators in `main.py` and `routes/*.py`.
   - Inspect export endpoints and document-save behavior.
4. Compare those findings with `docs/user_guide.md`. Record factual additions,
   removals, renames, and changed counts. Do not document aspirational features as live.
5. Ensure Investor Relations is prominent:
   - Feature the Press Release Creator near the beginning.
   - Explain Press Release Analyst versus Press Release Writer.
   - Cover web research, guided inputs, verification safeguards, all export actions,
     and Data Room save.
6. Update `docs/user_guide.md` to be the canonical current source.
7. Run the repository generator:

   ```bash
   python scripts/gen_platform_demo.py
   ```

8. Validate the output:
   - Confirm new filenames contain a UTC timestamp slug.
   - Confirm prior timestamped demo outputs moved to `docs/archive/<timestamp>/`.
   - Confirm the PDF opens, contains more than two pages, begins with cover then TOC,
     and every page after the cover has a visible page number.
   - Extract PDF text and confirm `Table of Contents`, `Investor Relations`,
     `Press Release Writer`, and `Page` are present.
9. Report the delta, generated paths, archive path, page count, and validation results.

## Document rules

- Title the document **LiquidRound AI Platform Demo**.
- Use slug format `liquidround-ai-platform-demo-YYYYMMDDTHHMMSSZ`.
- Put a page-numbered table of contents immediately after the cover.
- Include page numbers in PDF footers.
- Keep `docs/user_guide.md` usable by the in-app `/app/user-guide` route.
- Preserve unrelated files in `docs/` and all existing archive folders.
- Never overwrite or delete prior timestamped demo editions; archive them first.
