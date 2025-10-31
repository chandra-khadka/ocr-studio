bind = "0.0.0.0:8000"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
graceful_timeout = 30
keepalive = 5
loglevel = "info"
