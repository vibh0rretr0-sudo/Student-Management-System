# Learning — the visual study pack

Everything in this folder explains the project **without assuming you know
programming**. Start at the top; each file stands on its own.

| # | File | What it is | How to use it |
|---|------|------------|---------------|
| 01 | [`01_HOW_IT_WORKS_flowchart.png`](01_HOW_IT_WORKS_flowchart.png) | The 7-step story of one click: front desk → sorting office → filing cabinet / calculator → printing press | Read first — it's the same picture as on the README |
| 02 | [`02_ERD_WHITEBOARD_11_tables_15_arrows.png`](02_ERD_WHITEBOARD_11_tables_15_arrows.png) | The 11-table database drawn out: every table, all 15 foreign-key arrows color-coded, and the 2-minute drawing method | Practice drawing it from memory |
| 03 | [`03_VIVA_CHEAT_SHEET.png`](03_VIVA_CHEAT_SHEET.png) | One page: the numbers to memorize, the top 10 answers, the 60-second opener | Read in the corridor before the viva |
| 04 | [`04_CODE_MAP_every_file_explained.png`](04_CODE_MAP_every_file_explained.png) | **Every file in the project, in plain words** — grouped into 8 layers, from "what you see" down to the database (announcements, theme cookie and all) | Open it next to the code |
| 05 | [`05_CODE_MINDMAP_interactive.html`](05_CODE_MINDMAP_interactive.html) | The whole map as an **interactive mindmap** — click circles to fold/unfold, scroll to zoom, drag to pan | Open in any browser; needs internet on first view (the renderer loads from a CDN) |
| 06 | [`06_CODE_MINDMAP_static.png`](06_CODE_MINDMAP_static.png) | The same mindmap as a static picture (68 nodes) | View anywhere, including GitHub |

## Suggested order

1. **01** — the big picture (how a click becomes a page)
2. **04** or **05/06** — what every file does and how they connect
3. **02** — the database, arrow by arrow
4. **03** — the final revision pass

All diagrams follow the same cast of nicknames: the *front desk* (`server.py`),
the *sorting office* (`helpers.py`), the *page builders* (`routes/`), the
*clerks* (`models/`), the *vault* (`auth.py`), the *calculator room*
(`cpp_module/`), and the *filing cabinet* (the MySQL database).
