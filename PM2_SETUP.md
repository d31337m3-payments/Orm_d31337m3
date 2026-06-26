# PM2 Configuration for Frontend and Backend

## Files Created

1. `ecosystem.config.js` - PM2 configuration file for both frontend and backend
2. `/microservices/` - Directory containing OpenAPI specifications for all microservices (Stage 1 complete)

## Services Configuration

### Backend
- **Name**: backend
- **Script**: ./backend/server.py
- **Interpreter**: python3
- **Port**: 8000
- **Environment**: development

### Frontend
- **Name**: frontend
- **Script**: ./frontend/node_modules/react-scripts/scripts/start.js
- **Port**: 3000
- **Environment**: development

## Usage

### Install PM2 (if not already installed)
```bash
npm install -g pm2
```

### Start both applications
```bash
pm2 start ecosystem.config.js
```

### Monitor applications
```bash
pm2 monitor
```

### View logs
```bash
pm2 logs
```

### Stop all applications
```bash
pm2 stop all
```

### Delete all applications from PM2
```bash
pm2 delete all
```

## Microservices Status

**Stage 1 Complete**: Service boundaries and APIs have been defined
- Created OpenAPI specifications for all 6 microservices
- Next stage: Establish security boundaries

See `/microservices/STAGE_1_COMPLETE.md` for more details.
