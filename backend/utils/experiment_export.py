"""
Export and analysis utilities for experiment results
Provides tools for exporting experiment data to CSV/JSON and generating analysis reports
"""
import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from models import ExperimentExecution, QuestionResult, AgentExecutionConfig
from pathlib import Path


class ExperimentExporter:
    """Handles exporting experiment results to various formats"""
    
    def __init__(self, results_dir: str = "experiment_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
    
    def export_execution_to_csv(self, execution_id: int, session: Session) -> str:
        """Export execution results to CSV format for analysis"""
        
        execution = session.get(ExperimentExecution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Get all results for this execution
        results = session.exec(
            select(QuestionResult).where(
                QuestionResult.experiment_execution_id == execution_id
            )
        ).all()
        
        # Get agent configs for lookup
        agent_configs = session.exec(
            select(AgentExecutionConfig).where(
                AgentExecutionConfig.experiment_execution_id == execution_id
            )
        ).all()
        
        agent_config_map = {config.id: config for config in agent_configs}
        
        # Create filename
        timestamp = execution.started_at.strftime("%Y%m%d_%H%M%S")
        filename = f"execution_{execution_id}_{timestamp}.csv"
        filepath = self.results_dir / filename
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'execution_id', 'question_id', 'question_text', 'reference_answer',
                'agent_name', 'agent_team', 'system_prompt_used', 'user_prompt_used',
                'agent_response', 'score', 'processing_time_ms', 'llm_model',
                'error_occurred', 'response_timestamp', 'full_prompt_sent'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                agent_config = agent_config_map.get(result.agent_execution_config_id)
                
                # Parse evaluation metrics if available
                eval_metrics = {}
                if result.evaluation_metrics:
                    try:
                        eval_metrics = json.loads(result.evaluation_metrics)
                    except:
                        pass
                
                row = {
                    'execution_id': execution_id,
                    'question_id': result.question_id,
                    'question_text': result.question_text,
                    'reference_answer': result.reference_answer or '',
                    'agent_name': agent_config.agent_name_snapshot if agent_config else 'Unknown',
                    'agent_team': agent_config.agent_team_name_snapshot if agent_config else 'Unknown',
                    'system_prompt_used': agent_config.custom_system_prompt_applied or agent_config.system_prompt_snapshot if agent_config else '',
                    'user_prompt_used': agent_config.custom_user_prompt_applied or agent_config.user_prompt_snapshot if agent_config else '',
                    'agent_response': result.agent_response,
                    'score': result.score or '',
                    'processing_time_ms': result.processing_time_ms or '',
                    'llm_model': result.llm_model_used or '',
                    'error_occurred': result.error_occurred,
                    'response_timestamp': result.response_timestamp.isoformat(),
                    'full_prompt_sent': result.full_prompt_sent
                }
                
                # Add evaluation metrics as additional columns
                for metric_name, metric_value in eval_metrics.items():
                    if metric_name not in fieldnames:
                        # Add new columns for metrics not in original fieldnames
                        pass  # For now, skip extra metrics
                
                writer.writerow(row)
        
        return str(filepath)
    
    def export_execution_to_json(self, execution_id: int, session: Session) -> str:
        """Export complete execution trace to JSON for detailed analysis"""
        
        execution = session.get(ExperimentExecution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Get all related data
        results = session.exec(
            select(QuestionResult).where(
                QuestionResult.experiment_execution_id == execution_id
            )
        ).all()
        
        agent_configs = session.exec(
            select(AgentExecutionConfig).where(
                AgentExecutionConfig.experiment_execution_id == execution_id
            )
        ).all()
        
        # Build complete trace
        trace_data = {
            "execution_metadata": {
                "id": execution.id,
                "experiment_id": execution.experiment_id,
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "status": execution.status,
                "maestro_version": execution.maestro_version,
                "execution_environment": json.loads(execution.execution_environment) if execution.execution_environment else None,
                "total_questions_processed": execution.total_questions_processed,
                "processing_time_seconds": execution.processing_time_seconds,
                "summary_metrics": json.loads(execution.summary_metrics) if execution.summary_metrics else None
            },
            "dataset_snapshot": json.loads(execution.dataset_snapshot),
            "agent_configurations": [
                {
                    "id": config.id,
                    "agent_id": config.agent_id,
                    "agent_name": config.agent_name_snapshot,
                    "agent_team_name": config.agent_team_name_snapshot,
                    "system_prompt": config.system_prompt_snapshot,
                    "user_prompt": config.user_prompt_snapshot,
                    "variables": json.loads(config.variables_snapshot) if config.variables_snapshot else None,
                    "custom_overrides": {
                        "system_prompt": config.custom_system_prompt_applied,
                        "user_prompt": config.custom_user_prompt_applied,
                        "variables": json.loads(config.custom_variables_applied) if config.custom_variables_applied else None
                    },
                    "execution_settings": {
                        "active": config.active_in_execution,
                        "priority": config.execution_priority,
                        "questions_processed": config.questions_processed,
                        "average_response_time_ms": config.average_response_time_ms
                    }
                } for config in agent_configs
            ],
            "question_results": [
                {
                    "question_id": result.question_id,
                    "question_text": result.question_text,
                    "reference_answer": result.reference_answer,
                    "agent_execution_config_id": result.agent_execution_config_id,
                    "agent_response": result.agent_response,
                    "response_timestamp": result.response_timestamp.isoformat(),
                    "processing_time_ms": result.processing_time_ms,
                    "score": result.score,
                    "evaluation_metrics": json.loads(result.evaluation_metrics) if result.evaluation_metrics else None,
                    "full_prompt_sent": result.full_prompt_sent,
                    "llm_model_used": result.llm_model_used,
                    "llm_parameters": json.loads(result.llm_parameters) if result.llm_parameters else None,
                    "error_occurred": result.error_occurred,
                    "error_message": result.error_message
                } for result in results
            ]
        }
        
        # Create filename
        timestamp = execution.started_at.strftime("%Y%m%d_%H%M%S")
        filename = f"execution_{execution_id}_{timestamp}_trace.json"
        filepath = self.results_dir / filename
        
        # Write JSON
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(trace_data, jsonfile, indent=2, ensure_ascii=False)
        
        return str(filepath)


class ExperimentAnalyzer:
    """Provides analysis tools for experiment results"""
    
    def generate_execution_summary(self, execution_id: int, session: Session) -> Dict[str, Any]:
        """Generate a summary report for an execution"""
        
        execution = session.get(ExperimentExecution, execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Get results
        results = session.exec(
            select(QuestionResult).where(
                QuestionResult.experiment_execution_id == execution_id
            )
        ).all()
        
        # Get agent configs
        agent_configs = session.exec(
            select(AgentExecutionConfig).where(
                AgentExecutionConfig.experiment_execution_id == execution_id
            )
        ).all()
        
        # Calculate statistics
        total_questions = len(results)
        successful_responses = len([r for r in results if not r.error_occurred])
        error_rate = (total_questions - successful_responses) / total_questions if total_questions > 0 else 0
        
        scores = [r.score for r in results if r.score is not None]
        avg_score = sum(scores) / len(scores) if scores else None
        
        processing_times = [r.processing_time_ms for r in results if r.processing_time_ms is not None]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None
        
        # Agent performance breakdown
        agent_performance = {}
        for config in agent_configs:
            agent_results = [r for r in results if r.agent_execution_config_id == config.id]
            agent_scores = [r.score for r in agent_results if r.score is not None]
            agent_performance[config.agent_name_snapshot] = {
                "questions_answered": len(agent_results),
                "success_rate": len([r for r in agent_results if not r.error_occurred]) / len(agent_results) if agent_results else 0,
                "average_score": sum(agent_scores) / len(agent_scores) if agent_scores else None,
                "average_processing_time_ms": sum([r.processing_time_ms for r in agent_results if r.processing_time_ms]) / len(agent_results) if agent_results else None
            }
        
        return {
            "execution_id": execution_id,
            "experiment_id": execution.experiment_id,
            "execution_period": {
                "started_at": execution.started_at.isoformat(),
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "duration_seconds": execution.processing_time_seconds
            },
            "overall_statistics": {
                "total_questions": total_questions,
                "successful_responses": successful_responses,
                "error_rate": error_rate,
                "average_score": avg_score,
                "average_processing_time_ms": avg_processing_time
            },
            "agent_performance": agent_performance,
            "dataset_info": json.loads(execution.dataset_snapshot),
            "environment_info": json.loads(execution.execution_environment) if execution.execution_environment else None
        }
    
    def compare_executions(self, execution_ids: List[int], session: Session) -> Dict[str, Any]:
        """Compare multiple executions for analysis"""
        
        comparison_data = {
            "execution_count": len(execution_ids),
            "executions": [],
            "comparative_metrics": {}
        }
        
        all_scores = []
        all_processing_times = []
        
        for exec_id in execution_ids:
            summary = self.generate_execution_summary(exec_id, session)
            comparison_data["executions"].append(summary)
            
            # Collect scores and times for overall comparison
            results = session.exec(
                select(QuestionResult).where(
                    QuestionResult.experiment_execution_id == exec_id
                )
            ).all()
            
            all_scores.extend([r.score for r in results if r.score is not None])
            all_processing_times.extend([r.processing_time_ms for r in results if r.processing_time_ms is not None])
        
        # Calculate comparative metrics
        comparison_data["comparative_metrics"] = {
            "score_range": {
                "min": min(all_scores) if all_scores else None,
                "max": max(all_scores) if all_scores else None,
                "average": sum(all_scores) / len(all_scores) if all_scores else None
            },
            "processing_time_range": {
                "min": min(all_processing_times) if all_processing_times else None,
                "max": max(all_processing_times) if all_processing_times else None,
                "average": sum(all_processing_times) / len(all_processing_times) if all_processing_times else None
            }
        }
        
        return comparison_data


# Usage examples and utility functions
def export_all_execution_formats(execution_id: int, session: Session, results_dir: str = "experiment_results") -> Dict[str, str]:
    """Export execution in both CSV and JSON formats"""
    exporter = ExperimentExporter(results_dir)
    
    csv_path = exporter.export_execution_to_csv(execution_id, session)
    json_path = exporter.export_execution_to_json(execution_id, session)
    
    return {
        "csv_file": csv_path,
        "json_file": json_path
    }


def generate_experiment_report(execution_id: int, session: Session, output_dir: str = "reports") -> str:
    """Generate a complete experiment report with analysis and exports"""
    
    analyzer = ExperimentAnalyzer()
    exporter = ExperimentExporter()
    
    # Generate analysis
    summary = analyzer.generate_execution_summary(execution_id, session)
    
    # Export data
    csv_path = exporter.export_execution_to_csv(execution_id, session)
    json_path = exporter.export_execution_to_json(execution_id, session)
    
    # Create report
    report_dir = Path(output_dir)
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"experiment_report_{execution_id}_{timestamp}.json"
    
    report_data = {
        "report_generated_at": datetime.now().isoformat(),
        "execution_summary": summary,
        "exported_files": {
            "csv_data": csv_path,
            "full_trace": json_path
        },
        "reproducibility_info": {
            "note": "This report contains all information needed to reproduce this experiment",
            "dataset_snapshot_included": True,
            "agent_configurations_included": True,
            "full_prompts_included": True
        }
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    return str(report_path)
