import time

def run_experiment(experiment_id: str, config: dict):
    print(f"[Job] Starting experiment {experiment_id}")
    time.sleep(2)  # Simulate work
    print(f"[Job] Finished experiment {experiment_id}")
    return {"status": "completed", "results": {"accuracy": 0.89}}
