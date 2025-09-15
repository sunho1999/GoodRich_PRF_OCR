from core.config import settings

# Celery Configuration
broker_url = settings.redis_url
result_backend = settings.redis_url

# Task serialization
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Task routing
task_routes = {
    'apps.workers.tasks.process_pdf_pipeline': {'queue': 'pdf_processing'},
    'apps.workers.tasks.process_text_with_links': {'queue': 'text_processing'},
    'apps.workers.tasks.get_job_status': {'queue': 'status_check'},
    'apps.workers.tasks.cleanup_old_files': {'queue': 'maintenance'},
}

# Task execution
task_acks_late = True
worker_prefetch_multiplier = 1
task_compression = 'gzip'
result_compression = 'gzip'

# Task timeouts
task_soft_time_limit = 300  # 5 minutes
task_time_limit = 600  # 10 minutes

# Result backend
result_expires = 3600  # 1 hour
result_persistent = True

# Worker settings
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 200000  # 200MB

# Beat schedule (for periodic tasks)
beat_schedule = {
    'cleanup-old-files': {
        'task': 'apps.workers.tasks.cleanup_old_files',
        'schedule': 86400.0,  # Daily
        'args': (7,),  # Clean files older than 7 days
    },
}
