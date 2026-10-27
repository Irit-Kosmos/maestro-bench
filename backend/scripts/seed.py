#!/usr/bin/env python3
# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Seed script for development/testing.
Creates prompts, models, agents, and the sample datasets.

It only adds what is missing (matched by name) and never deletes or edits
anything, so it is safe to run on a database that already holds your data, and
to run again. It works inside one workspace (the "default" one unless told
otherwise) and never touches the others.

Usage (from the backend/ directory):
    uv run python scripts/seed.py [--workspace SLUG]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# Allow running from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from sqlmodel import Session, SQLModel, select

import workspace_files
from db import engine, init_db
from tables import (
    Agent,
    Dataset,
    Model,
    Prompt,
    PromptVersion,
    Tag,
    TagLink,
    Workspace,
)
from workspace_scope import scope_session


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


SAMPLE_DATASETS_DIR = Path(__file__).parent / "sample_datasets"


def _copy_sample_dataset(workspace_id: int, file_name: str) -> None:
    """Put a sample dataset file in the workspace's folder, unless it is there."""
    target = workspace_files.datasets_dir(workspace_id) / file_name
    if target.exists():
        return
    source = SAMPLE_DATASETS_DIR / file_name
    if not source.is_file():
        print(f"  Sample file not found, skipped: {source}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


created_counts: dict[str, int] = {}


def seed_data(workspace: str = "default") -> None:
    """Create initial data for development/testing in a workspace."""

    init_db()
    created_counts.clear()

    with Session(engine) as session:
        target = session.exec(select(Workspace).where(Workspace.slug == workspace)).first()
        if target is None:
            sys.exit(f"No workspace {workspace!r}: create it first")
        scope_session(session, target.id)
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
        # 3. Agents
        # ------------------------------------------------------------------
        print("Creating agents...")
        _get_or_create(
            session,
            Agent,
            {"name": "Language"},
            description="Evaluates learner answers based on clarity, grammar, and terminology",
            default_prompt_version_id=language_version.id,
        )
        _get_or_create(
            session,
            Agent,
            {"name": "Content"},
            description="Evaluates how well learner answers cover key factual and conceptual points",
            default_prompt_version_id=content_version.id,
        )
        _get_or_create(
            session,
            Agent,
            {"name": "Metatutor"},
            description="Provides actionable insights and advice for teachers",
            default_prompt_version_id=metatutor_version.id,
        )

        # ------------------------------------------------------------------
        # 4. Sample datasets (files are copied into the workspace's datasets folder)
        # ------------------------------------------------------------------
        print("Creating datasets...")
        for file_name in ("mohler_dataset.csv", "diff_gt_2_mohler_dataset.csv"):
            _copy_sample_dataset(target.id, file_name)
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
    parser = argparse.ArgumentParser(description="Add the sample data to a workspace")
    parser.add_argument(
        "--workspace", default="default", help="slug of the workspace (default: default)"
    )
    seed_data(parser.parse_args().workspace)
