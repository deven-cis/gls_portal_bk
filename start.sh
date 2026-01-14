#!/bin/bash

echo "Starting GLS Portal Backend with Honcho..."
echo ""
echo "Services that will start:"
echo "  1. Redis (broker) - port 6379"
echo "  2. FastAPI (web) - port 8000"
echo "  3. Celery Worker - processes tasks"
echo "  4. Celery Beat - scheduler (updates job status every minute)"
echo ""
echo "Log for each service will be prefixed with the service name"
echo ""
echo "Press Ctrl+C to stop all services"
echo "-------------------------------------------"
echo ""

honcho start
