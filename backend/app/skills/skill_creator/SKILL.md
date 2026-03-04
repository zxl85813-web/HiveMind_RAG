---
name: skill-creator
description: Meta-skill used to scaffold, code, and test new Skills.
version: "0.1.0"
---

# Skill Creator Skill

This is a meta-skill. It allows the agent to self-replicate new capabilities by generating standard boilerplate, registering `SKILL.md` configurations, and creating functional LangChain `@tool` sets inside `tools.py`.

## Flow

1. Define a need
2. Scaffold a folder in `app/skills/<name>`
3. Write `SKILL.md`
4. Write `tools.py`
5. Test the tools
6. Dynamic registry reloading makes it available immediately
