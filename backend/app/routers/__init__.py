"""FastAPI route handlers.

Router modules:
  - auth.py           POST /auth/anonymous, /auth/magic-link, GET /auth/session
  - me.py             GET|PUT /me
  - birth_profiles.py CRUD /me/profile
  - charts.py         POST /charts, GET /charts/:id (planned)
  - transits.py       POST|GET /charts/:id/transits (planned)
  - synastry.py       CRUD /synastry (planned)
  - life_phases.py    POST|GET /me/life-phases (planned)
  - conversations.py  CRUD /conversations (planned)
  - stream.py         SSE /stream (planned)
"""

# Each router module is included via ``app.main`` — see ``main.py`` for the
# full list of ``app.include_router(...)`` calls.
