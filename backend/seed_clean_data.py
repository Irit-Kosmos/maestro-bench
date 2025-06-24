#!/usr/bin/env python3
"""
Clean seed script for the updated MAESTRO architecture
Creates prompts, models, agent teams, and agents with proper relationships
"""

import json
from datetime import datetime
from sqlmodel import Session, select
from db import engine
from models import Model, Prompt, PromptVersion, AgentTeam, Agent, Dataset


def seed_data():
    """Create initial data for development/testing with the new architecture"""
    
    with Session(engine) as session:
        # Clear existing data in proper order (FK dependencies)
        print("Clearing existing data...")
        
        # Delete agents first
        for agent in session.exec(select(Agent)).all():
            session.delete(agent)
        
        # Delete agent teams
        for team in session.exec(select(AgentTeam)).all():
            session.delete(team)
            
        # Delete prompt versions
        for version in session.exec(select(PromptVersion)).all():
            session.delete(version)
            
        # Delete prompts
        for prompt in session.exec(select(Prompt)).all():
            session.delete(prompt)
            
        # Delete models
        for model in session.exec(select(Model)).all():
            session.delete(model)

        # Delete datasets (if any)
        for dataset in session.exec(select(Dataset)).all():
            session.delete(dataset)
            
        session.commit()
        print("Existing data cleared.")

        mistral_models = [
            "mistral-medium-2505",
            "mistral-small-2503",
            "magistral-small-2506",
            "magistral-medium-2506"
        ]

        # 1. Create Models
        print("Creating models...")
        for model_name in mistral_models:
            model = Model(
                name=model_name,
                provider="mistral",
                description=f"Mistral model {model_name}",
                is_active=True
            )
            session.add(model)
        session.commit()

        # 2. Create Prompts and PromptVersions
        print("Creating prompts and versions...")
        
        # Language Evaluation Prompt
        language_prompt = Prompt(
            name="Language Evaluator",
            description="Evaluates learner answers based on clarity, grammar, and terminology",
            category="evaluation"
        )
        session.add(language_prompt)
        session.commit()
        session.refresh(language_prompt)
        
        language_version = PromptVersion(
            prompt_id=language_prompt.id,
            version="1.0",
            system_prompt="You are a Language agent with deep knowledge of educational science and cognitive psychology",
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
            temperature=0.7,
            is_active=True,
            is_default=True
        )
        session.add(language_version)
        
        # Content Evaluation Prompt
        content_prompt = Prompt(
            name="Content Evaluator",
            description="Evaluates how well learner answers cover key factual and conceptual points",
            category="evaluation"
        )
        session.add(content_prompt)
        session.commit()
        session.refresh(content_prompt)
        
        content_version = PromptVersion(
            prompt_id=content_prompt.id,
            version="1.0",
            system_prompt="You are a Content agent with deep knowledge of educational science and cognitive psychology",
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
            is_default=True
        )
        session.add(content_version)
        
        # MetaTutor Prompt
        metatutor_prompt = Prompt(
            name="MetaTutor",
            description="Provides actionable insights and advice for teachers",
            category="advice"
        )
        session.add(metatutor_prompt)
        session.commit()
        session.refresh(metatutor_prompt)
        
        metatutor_version = PromptVersion(
            prompt_id=metatutor_prompt.id,
            version="1.0",
            system_prompt="""You are a MetaTutor agent with deep knowledge of educational science and cognitive psychology.
You provide actionable insights or advice for a teacher, based on the teacher's question 
and the final explanation from the system.""",
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
            is_default=True
        )
        session.add(metatutor_version)
        
        session.commit()
        session.refresh(language_version)
        session.refresh(content_version)
        session.refresh(metatutor_version)

        # 3. Create Agent Teams
        print("Creating agent teams...")
        
        corrector_team = AgentTeam(
            name="Corrector",
            description="Agent team focused on evaluating and correcting learner responses"
        )
        
        metatutor_team = AgentTeam(
            name="Metatutor",
            description="Agent team providing actionable insights and advice for teachers"
        )
        
        session.add(corrector_team)
        session.add(metatutor_team)
        session.commit()
        session.refresh(corrector_team)
        session.refresh(metatutor_team)

        # 4. Create Agents
        print("Creating agents...")
        
        # Language Agent (Corrector team)
        language_agent = Agent(
            name="Language",
            description="Evaluates learner answers based on clarity, grammar, and terminology",
            default_prompt_version_id=language_version.id,
            team_id=corrector_team.id
        )
        
        # Content Agent (Corrector team)
        content_agent = Agent(
            name="Content",
            description="Evaluates how well learner answers cover key factual and conceptual points",
            default_prompt_version_id=content_version.id,
            team_id=corrector_team.id
        )
        
        # MetaTutor Agent (MetaTutor team)
        metatutor_agent = Agent(
            name="Metatutor",
            description="Provides actionable insights and advice for teachers based on responses and queries",
            default_prompt_version_id=metatutor_version.id,
            team_id=metatutor_team.id
        )
        
        session.add(language_agent)
        session.add(content_agent)
        session.add(metatutor_agent)
        
        session.commit()

        # 5. Dataset Creation (if needed)
        print("Creating datasets...")
        dataset = Dataset(
            name="Mohler",
            description="Mohler dataset",
            file_path="mohler_dataset.csv",
            created_at=datetime.utcnow()
        )

        session.add(dataset)
        session.commit()

        print("\n✅ Clean architecture successfully seeded!")

if __name__ == "__main__":
    seed_data()
