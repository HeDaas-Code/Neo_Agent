#!/bin/bash
cd /home/hedass/桌面/Lien_os
source venv/bin/activate
exec python -m neo_agent.service.daemon
