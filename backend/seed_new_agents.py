#!/usr/bin/env python3
"""
Seed script to create initial agent teams and agents for testing
"""

import asyncio
from datetime import datetime
from sqlmodel import Session, select
from db import engine
from models import AgentTeam, Agent
import json

def seed_data():
    """Create initial agent teams and agents for development/testing"""
    
    with Session(engine) as session:
        # Check if data already exists
        existing_teams = session.exec(select(AgentTeam)).first()
        if existing_teams:
            print("Data already exists. Clearing existing data...")
            # Clear existing data
            session.exec(select(Agent)).all()
            for agent in session.exec(select(Agent)).all():
                session.delete(agent)
            for team in session.exec(select(AgentTeam)).all():
                session.delete(team)
            session.commit()
        
        # Agent team 1: Corrector
        corrector_team = AgentTeam(
            name="Corrector",
            description="Agent team focused on evaluating and correcting learner responses"
        )
        session.add(corrector_team)
        session.commit()
        session.refresh(corrector_team)

        # Agent team 2: Metatutor  
        metatutor_team = AgentTeam(
            name="Metatutor",
            description="Agent team providing actionable insights and advice for teachers"
        )
        session.add(metatutor_team)
        session.commit()
        session.refresh(metatutor_team)

        # Create agents for Corrector team
        language_agent = Agent(
            name="Language",
            description="Evaluates learner answers based on clarity, grammar, and terminology",
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
            team_id=corrector_team.id
        )

        content_agent = Agent(
            name="Content",
            description="Evaluates how well learner answers cover key factual and conceptual points",
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

Return a **probability distribution** over [0, 1, 2, 3, 4, 5] based on your confidence in the match. If unsure, distribute some probability over adjacent values.

Output JSON format:
{
  "score": [p0, p1, p2, p3, p4, p5],
  "reasoning": "..."  // max 1 sentence
}

Input:
<question></question>
<reference_answer></reference_answer>
<learner_answer></learner_answer>""",
            variables=json.dumps(["question", "reference_answer", "learner_answer"]),
            team_id=corrector_team.id
        )

        # Create agent for Metatutor team
        metatutor_agent = Agent(
            name="Metatutor",
            description="Provides actionable insights and advice for teachers based on responses and queries",
            system_prompt="""You are a MetaTutor agent with deep knowledge of educational science and cognitive psychology.
            You provide actionable insights or advice for a teacher, based on the teacher's question 
            and the final explanation from the system.""",
            user_prompt="""Teacher's original query: '<query>
<query></query>
</query>'

Response provided to the teacher: '<response>
<response></response>
</response>'

Based on the teacher's query and the response, provide actionable advice for the teacher. You must take a decision based only on the context provided. The actions are not related: each action should be different and provide diverse advice to the teacher. You need to take 2 action types from the following list and provide a brief explanation of why you chose each action type. The goal is to provide diverse and actionable advice to the teacher to help them improve their teaching.

To help the learner, you can take the following actions:
1. ENGAGE: Engage the learner by working more (best suited to low engagement learners).
2. EXPLAIN: Provide detailed explanations to the learner based on their answers (best suited to low performance learners).
3. CONGRATULATE: Give positive encouragement to the learner (suited to all learners).
4. RECOMMEND: Recommend additional resources to the learner (suited to all learners).

You should respond with a JSON containing 'data' which is an array of an object with the 'action_type' and 'explanation' fields for each values.
Your response must be in the same language as the query!""",
            variables=json.dumps(["query", "response"]),
            team_id=metatutor_team.id
        )

        # Add all agents
        session.add(language_agent)
        session.add(content_agent)
        session.add(metatutor_agent)
        
        session.commit()
        
        print(f"Successfully created 2 agent teams and 3 agents!")
        
        # Print summary
        print("\nCreated Teams:")
        print(f"  - {corrector_team.name} (ID: {corrector_team.id})")
        print(f"  - {metatutor_team.name} (ID: {metatutor_team.id})")
        
        print("\nCreated Agents:")
        print(f"  - {language_agent.name} (ID: {language_agent.id}) - Team: {corrector_team.name}")
        print(f"  - {content_agent.name} (ID: {content_agent.id}) - Team: {corrector_team.name}")
        print(f"  - {metatutor_agent.name} (ID: {metatutor_agent.id}) - Team: {metatutor_team.name}")

if __name__ == "__main__":
    seed_data()
