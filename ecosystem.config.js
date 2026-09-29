module.exports = {
  apps: [
    {
      name: "expense-tracker-api",
      cwd: "/home/kurieneapenk_dev/expense-tracker/backend",
      script: "/home/kurieneapenk_dev/expense-tracker/.venv/bin/uvicorn",
      args: "app.main:app --host 127.0.0.1 --port 8000 --workers 1",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "150M",
      env: {
        PYTHONPATH: "/home/kurieneapenk_dev/expense-tracker/backend",
        PORT: 8000,
        SQLITE_WAL_MODE: "true"
      }
    }
  ]
};
