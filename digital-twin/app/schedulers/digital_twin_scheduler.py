import logging
import time
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from app.services.supabase_client import get_enrolled_user_ids
from app.services.twin_orchestrator import run_digital_twin

logger = logging.getLogger(__name__)

# Core scheduler configuration
executors = {
    'default': ThreadPoolExecutor(max_workers=5)
}

job_defaults = {
    'coalesce': True,          # Coalesce multiple missed executions into a single run
    'max_instances': 1         # Restrict duplicate simultaneous executions
}

scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

def get_enrolled_learners() -> List[str]:
    """
    Retrieves unique list of active learner IDs via Supabase REST API.
    Queries the enrollments table, falls back to learner_activity_events.
    """
    return get_enrolled_user_ids()


def execute_digital_twin_job() -> None:
    """
    Cron job triggered every minute. Iterates through all users to track and re-engage.
    """
    job_start = time.time()
    logger.info("DigitalTwinScheduler: Starting evaluation cron job.")
    
    learners = get_enrolled_learners()
    logger.info(f"DigitalTwinScheduler: Evaluating {len(learners)} users.")
    
    for learner_id in learners:
        try:
            run_digital_twin(learner_id)
        except Exception as e:
            logger.error(f"DigitalTwinScheduler: Failed to evaluate learner {learner_id}: {e}")
            
    job_duration = time.time() - job_start
    logger.info(f"DigitalTwinScheduler: Evaluation cron job completed in {job_duration:.2f} seconds.")


def start_scheduler() -> None:
    """
    Starts the scheduler process and adds the interval job.
    """
    if not scheduler.running:
        scheduler.add_job(
            execute_digital_twin_job,
            trigger='interval',
            minutes=1,
            id='digital_twin_job',
            replace_existing=True
        )
        scheduler.start()
        logger.info("DigitalTwinScheduler background scheduler started successfully.")


def shutdown_scheduler() -> None:
    """
    Terminates the background scheduler threads.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("DigitalTwinScheduler background scheduler stopped.")
