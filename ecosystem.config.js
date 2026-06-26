module.exports = {
  apps: [
    {
      name: "backend",
      script: "./backend/server.py",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "development",
        PORT: 8000,
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
