# logs cpu and gpu stats - started in CRON
# results can be seen in idmy.team/stats

import subprocess, string
import psutil
from settings import functions, config

conn = functions.DB.conn(config.DB["username"], config.DB["password"], config.DB["db"])

gpu = subprocess.check_output('nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv', shell=True).split("\n",2)[1]
gpu_split = string.split(gpu, "%, ")

gpu_util = gpu_split[0]
gpu_mib = string.split(gpu_split[1], "MiB")[0]
cpu_util = psutil.cpu_percent()

functions.log_data(conn, "Utilization", "GPU", "Utilization", gpu_util.strip(), yaxis="%")
functions.log_data(conn, "Memory Usage", "GPU", "Memory", gpu_mib.strip(), yaxis="MiB")
functions.log_data(conn, "Utilization", "CPU", "Utilization", str(cpu_util).strip(), yaxis="%")

# TODO remove data older than an hour
