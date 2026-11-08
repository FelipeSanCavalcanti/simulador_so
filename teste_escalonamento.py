
from fs_simulador.io_scheduler import DiskScheduler

scheduler = DiskScheduler(
    total_tracks=16,
    head_position=8
)

requests = [12, 3, 14, 5, 1]

scheduler.schedule(requests, "FCFS")
scheduler.schedule(requests, "SSTF")
scheduler.schedule(requests, "SCAN")
scheduler.schedule(requests, "C-SCAN")
