import time
from datetime import datetime
from sqlmodel import Session
from db import engine
from models import Experiment

def run_experiment(experiment_id: int):
    """Run an experiment - simulates the actual experiment process"""
    print(f"[Job] Starting experiment {experiment_id}")
    
    try:
        with Session(engine) as session:
            # Get the experiment
            experiment = session.get(Experiment, experiment_id)
            if not experiment:
                print(f"[Job] Error: Experiment {experiment_id} not found")
                return {"status": "failed", "error": "Experiment not found"}
            
            # Update status to running
            experiment.status = "running"
            session.add(experiment)
            session.commit()
            print(f"[Job] Experiment {experiment_id} status updated to 'running'")
            
            # Simulate experiment work (5 seconds)
            print(f"[Job] Processing experiment '{experiment.name}'...")
            time.sleep(5)
            
            # Update status to completed
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()
            session.add(experiment)
            session.commit()
            
            print(f"[Job] Experiment {experiment_id} completed successfully")
            return {
                "status": "completed", 
                "experiment_id": experiment_id,
                "name": experiment.name,
                "completed_at": experiment.completed_at.isoformat(),
                "results": {"message": "Experiment simulation completed"}
            }
            
    except Exception as e:
        print(f"[Job] Error processing experiment {experiment_id}: {str(e)}")
        
        # Try to update status to failed
        try:
            with Session(engine) as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment:
                    experiment.status = "failed"
                    session.add(experiment)
                    session.commit()
        except Exception as update_error:
            print(f"[Job] Failed to update experiment status to failed: {update_error}")
        
        return {"status": "failed", "error": str(e)}
