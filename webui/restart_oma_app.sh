#!/bin/bash
pkill -f run_oma_app.sh
pkill -f oma_streamlit_app.py
nohup ~/workspace/oma/webui/run_oma_app.sh &

