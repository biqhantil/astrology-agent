"""Pydantic v2 request/response schemas.

Each domain gets a module:
  - auth.py          Auth request/response schemas
  - user.py          User profile schemas
  - birth_profile.py Birth profile schemas
  - chart.py         Chart schemas (planned)
  - transit.py       Transit schemas (planned)
  - synastry.py      Synastry schemas (planned)
  - life_phase.py    Life phase schemas (planned)
  - conversation.py  Conversation schemas (planned)
  - message.py       Message schemas (planned)
"""

# Modules are imported directly by their consumers (routers, tests) to keep
# the dependency graph explicit and avoid star-import pollution.
