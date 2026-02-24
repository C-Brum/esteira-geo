#!/bin/bash
set -e

# Script to run the processing pipeline
# Sourced by cron job

cd /home/esteira/esteira-geo
source venv/bin/activate

export $(cat .env | grep -v '^#')

# Run the main processing script
python3 main.py >> logs/pipeline.log 2>&1

echo "Pipeline execution completed at $(date)" >> logs/pipeline.log
