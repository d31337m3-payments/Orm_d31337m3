module.exports = {
  apps: [
    {
      name: "orchestrator",
      script: "./microservices/orchestrator/service/main.py",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "development",
        PORT: 8006,
      },
    },
    {
      name: "frontend",
      script: "./frontend/node_modules/react-scripts/scripts/start.js",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "development",
        PORT: 3000,
      },
    }
  ]
};
