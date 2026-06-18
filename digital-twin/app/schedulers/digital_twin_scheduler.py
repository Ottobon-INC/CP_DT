import logging
import time
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from app.services.supabase_client import get_enrolled_user_ids, _get
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


def execute_module_deadline_job() -> None:
    """
    Daily job: Checks if modules have been in progress for over a week and
    dispatches friendly check-in emails if needed.
    """
    from app.services.module_deadline import check_module_deadlines
    
    job_start = time.time()
    logger.info("ModuleDeadlineJob: Starting daily module deadline check.")
    
    learners = get_enrolled_learners()
    
    for learner_id in learners:
        try:
            enrollment_rows = _get("enrollments", {
                "select": "course_id",
                "user_id": f"eq.{learner_id}",
                "status": "eq.active",
            })
            course_ids = list({r.get("course_id") for r in enrollment_rows if r.get("course_id")})
            
            for course_id in course_ids:
                check_module_deadlines(learner_id, course_id)
        except Exception as e:
            logger.error(f"ModuleDeadlineJob: Failed for learner {learner_id}: {e}")
            
    job_duration = time.time() - job_start
    logger.info(f"ModuleDeadlineJob: Completed in {job_duration:.2f} seconds.")


def execute_engagement_snapshot_job() -> None:
    """
    Daily job: Captures engagement snapshots for all enrolled learners across all courses.
    Stores a daily record of progress, quiz performance, login activity, and engagement score.
    """
    from app.services.engagement_tracker import capture_engagement_snapshot
    
    job_start = time.time()
    logger.info("EngagementSnapshotJob: Starting daily snapshot capture.")
    
    learners = get_enrolled_learners()
    
    for learner_id in learners:
        try:
            enrollment_rows = _get("enrollments", {
                "select": "course_id",
                "user_id": f"eq.{learner_id}",
                "status": "eq.active",
            })
            course_ids = list({r.get("course_id") for r in enrollment_rows if r.get("course_id")})
            
            for course_id in course_ids:
                capture_engagement_snapshot(learner_id, course_id)
        except Exception as e:
            logger.error(f"EngagementSnapshotJob: Failed for learner {learner_id}: {e}")
    
    job_duration = time.time() - job_start
    logger.info(f"EngagementSnapshotJob: Completed in {job_duration:.2f} seconds.")


def start_scheduler() -> None:
    """
    Starts the scheduler process and adds all interval/cron jobs.
    """
    if not scheduler.running:
        # Every-minute inactivity check job
        scheduler.add_job(
            execute_digital_twin_job,
            trigger='interval',
            minutes=1,
            id='digital_twin_job',
            replace_existing=True
        )
        
        # Daily module deadline check (runs at 6:00 AM UTC)
        scheduler.add_job(
            execute_module_deadline_job,
            trigger='cron',
            hour=6,
            minute=0,
            id='module_deadline_job',
            replace_existing=True
        )
        
        # Daily engagement snapshot (runs at 7:00 AM UTC)
        scheduler.add_job(
            execute_engagement_snapshot_job,
            trigger='cron',
            hour=7,
            minute=0,
            id='engagement_snapshot_job',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(
            "DigitalTwinScheduler started with 3 jobs: "
            "inactivity (1min), module_deadlines (daily 6AM), engagement_snapshots (daily 7AM)"
        )


def shutdown_scheduler() -> None:
    """
    Terminates the background scheduler threads.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("DigitalTwinScheduler background scheduler stopped.")

