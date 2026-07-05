"""Scenario-based integration tests for the Astrology Agent API.

Each scenario defines a sequence of user messages/interactions with the
backend and expected assertions. The scenario runner sends prompts to the
real API, collects metrics, and produces a JSONL report.

To run all scenarios::

    python -m tests.scenario_runner

To run a specific scenario::

    python -m tests.scenario_runner --scenario birth_chart_creation
"""
