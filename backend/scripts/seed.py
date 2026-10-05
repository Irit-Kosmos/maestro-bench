#!/usr/bin/env python3
"""
Seed script for development/testing.
Creates prompts, models, agent teams, agents, and the sample datasets.

It only adds what is missing (matched by name) and never deletes or edits
anything, so it is safe to run on a database that already holds your data, and
to run again.

Usage (from the backend/ directory):
    uv run python scripts/seed.py
"""

import json
import sys
from pathlib import Path

# Allow running from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from sqlmodel import Session, SQLModel, select

from db import engine, init_db
from tables import (
    Agent,
    AgentTeam,
    Dataset,
    Model,
    Prompt,
    PromptVersion,
    Tag,
    TagLink,
)


def _get_or_create(session: Session, model: type[SQLModel], lookup: dict, **fields):
    """Return the row matching ``lookup``, creating it with ``fields`` if missing."""
    existing = session.exec(select(model).filter_by(**lookup)).first()
    if existing:
        return existing
    created = model(**lookup, **fields)
    session.add(created)
    session.flush()
    created_counts[model.__name__] = created_counts.get(model.__name__, 0) + 1
    return created


def _get_or_create_tag(session: Session, name: str, color: str) -> Tag:
    """Tag names are unique ignoring case."""
    existing = session.exec(select(Tag).where(func.lower(Tag.name) == name.lower())).first()
    return existing or _get_or_create(session, Tag, {"name": name}, color=color)


def _tag(session: Session, tag: Tag, prompt: Prompt) -> None:
    _get_or_create(
        session, TagLink, {"tag_id": tag.id, "kind": "prompt", "item_id": prompt.id}
    )


created_counts: dict[str, int] = {}


def seed_data() -> None:
    """Create initial data for development/testing."""

    init_db()
    created_counts.clear()

    with Session(engine) as session:
        # ------------------------------------------------------------------
        # 1. Models
        # ------------------------------------------------------------------
        print("Creating models...")
        mistral_models = [
            "mistral-medium-2505",
            "mistral-small-2503",
            "magistral-small-2506",
            "magistral-medium-2506",
        ]
        for model_name in mistral_models:
            _get_or_create(
                session,
                Model,
                {"name": model_name, "provider": "mistral"},
                description=f"Mistral model {model_name}",
                is_active=True,
            )

        # ------------------------------------------------------------------
        # 2. Prompts & PromptVersions
        # ------------------------------------------------------------------
        print("Creating prompts and versions...")

        evaluation_tag = _get_or_create_tag(session, "evaluation", "blue")
        advice_tag = _get_or_create_tag(session, "advice", "green")

        # Language Evaluator
        language_prompt = _get_or_create(
            session,
            Prompt,
            {"name": "Language Evaluator"},
            description="Evaluates learner answers based on clarity, grammar, and terminology",
        )
        _tag(session, evaluation_tag, language_prompt)

        language_version = _get_or_create(
            session,
            PromptVersion,
            {"prompt_id": language_prompt.id, "version": "1.0"},
            system_prompt=(
                "You are a Language agent with deep knowledge of educational science "
                "and cognitive psychology"
            ),
            user_prompt="""You are a Language Evaluation Agent.

Evaluate the learner's answer based on clarity, grammar, and use of appropriate terminology.

Use this scale:
- **5**: Clear, well-structured, grammatically flawless, and uses correct terminology.
- **4**: Mostly clear and grammatical, with minor issues or slightly imprecise language.
- **3**: Understandable but awkward or inconsistent, with several errors.
- **2**: Hard to follow — many errors or awkward phrasing.
- **1**: Poorly written — mostly ungrammatical or confusing.
- **0**: Incomprehensible or gibberish.

Return a **probability distribution** over [0, 1, 2, 3, 4, 5] based on how well the answer communicates its ideas.

Output JSON format:
{
  "score": [p0, p1, p2, p3, p4, p5],
  "reasoning": "..."  // max 1 sentence
}

Input:
<learner_answer></learner_answer>""",
            variables=json.dumps(["learner_answer"]),
            is_active=True,
            is_default=True,
        )

        # Content Evaluator
        content_prompt = _get_or_create(
            session,
            Prompt,
            {"name": "Content Evaluator"},
            description="Evaluates how well learner answers cover key factual and conceptual points",
        )
        _tag(session, evaluation_tag, content_prompt)

        content_version = _get_or_create(
            session,
            PromptVersion,
            {"prompt_id": content_prompt.id, "version": "1.0"},
            system_prompt=(
                "You are a Content agent with deep knowledge of educational science "
                "and cognitive psychology"
            ),
            user_prompt="""You are a Content Evaluation Agent.

Evaluate how well the learner's answer covers the key factual and conceptual points in the reference answer.

Use this scoring scale:
- **5**: Complete match — all major points are covered clearly and correctly.
- **4**: Mostly correct — 1–2 minor points are missing or unclear.
- **3**: Partially correct — some relevant content, but several important aspects are missing or vague.
- **2**: Limited correctness — only a few relevant ideas, with some errors or confusion.
- **1**: Minimal overlap — mostly incorrect or off-topic.
- **0**: Completely incorrect or irrelevant.

Return a **probability distribution** over [0, 1, 2, 3, 4, 5] based on your confidence in the match.

Output JSON format:
{
  "score": [p0, p1, p2, p3, p4, p5],
  "reasoning": "..."  // max 1 sentence
}

Input:
<learner_answer></learner_answer>
<reference_answer></reference_answer>""",
            variables=json.dumps(["learner_answer", "reference_answer"]),
            is_active=True,
            is_default=True,
        )

        # MetaTutor
        metatutor_prompt = _get_or_create(
            session,
            Prompt,
            {"name": "MetaTutor"},
            description="Provides actionable insights and advice for teachers",
        )
        _tag(session, advice_tag, metatutor_prompt)

        metatutor_version = _get_or_create(
            session,
            PromptVersion,
            {"prompt_id": metatutor_prompt.id, "version": "1.0"},
            system_prompt=(
                "You are a MetaTutor agent with deep knowledge of educational science and "
                "cognitive psychology.\n"
                "You provide actionable insights or advice for a teacher, based on the "
                "teacher's question and the final explanation from the system."
            ),
            user_prompt="""Teacher's original query: '<query></query>'

Response provided to the teacher: '<response></response>'

Based on the teacher's query and the response, provide actionable advice for the teacher. You must take 2 action types from the following list and provide a brief explanation of why you chose each action type. The goal is to provide diverse and actionable advice to the teacher to help them improve their teaching.

To help the learner, you can take the following actions:
1. ENGAGE: Engage the learner by working more (best suited to low engagement learners).
2. EXPLAIN: Provide detailed explanations to the learner based on their answers (best suited to low performance learners).
3. CONGRATULATE: Give positive encouragement to the learner (suited to all learners).
4. RECOMMEND: Recommend additional resources to the learner (suited to all learners).

You should respond with a JSON containing 'data' which is an array of an object with the 'action_type' and 'explanation' fields for each values.
Your response must be in the same language as the query!""",
            variables=json.dumps(["query", "response"]),
            is_active=True,
            is_default=True,
        )


        # ------------------------------------------------------------------
        # 3. Agent Teams
        # ------------------------------------------------------------------
        print("Creating agent teams...")
        corrector_team = _get_or_create(
            session,
            AgentTeam,
            {"name": "Corrector"},
            description="Agent team focused on evaluating and correcting learner responses",
        )
        metatutor_team = _get_or_create(
            session,
            AgentTeam,
            {"name": "Metatutor"},
            description="Agent team providing actionable insights and advice for teachers",
        )

        # ------------------------------------------------------------------
        # 4. Agents
        # ------------------------------------------------------------------
        print("Creating agents...")
        _get_or_create(
            session,
            Agent,
            {"name": "Language", "team_id": corrector_team.id},
            description="Evaluates learner answers based on clarity, grammar, and terminology",
            default_prompt_version_id=language_version.id,
        )
        _get_or_create(
            session,
            Agent,
            {"name": "Content", "team_id": corrector_team.id},
            description="Evaluates how well learner answers cover key factual and conceptual points",
            default_prompt_version_id=content_version.id,
        )
        _get_or_create(
            session,
            Agent,
            {"name": "Metatutor", "team_id": metatutor_team.id},
            description="Provides actionable insights and advice for teachers",
            default_prompt_version_id=metatutor_version.id,
        )

        # ------------------------------------------------------------------
        # 5. Sample datasets (files live in <DATA_DIR>/datasets)
        # ------------------------------------------------------------------
        print("Creating datasets...")
        _get_or_create(
            session,
            Dataset,
            {"file_path": "mohler_dataset.csv"},
            name="Mohler",
            description="Mohler short-answer grading dataset (Mohler et al., 2011)",
        )
        _get_or_create(
            session,
            Dataset,
            {"file_path": "diff_gt_2_mohler_dataset.csv"},
            name="Mohler (score gap > 2)",
            description="Subset of the Mohler dataset where the two graders disagree by more than 2 points",
        )

        session.commit()

    if created_counts:
        added = ", ".join(f"{count} {name}" for name, count in created_counts.items())
        print(f"\nSeeded: added {added}.")
    else:
        print("\nNothing to add: the sample data is already there.")


if __name__ == "__main__":
    seed_data()
