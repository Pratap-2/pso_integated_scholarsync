import time
from chatbot.sync.sync_worker import run_sync

while True:

    run_sync()

    time.sleep(600)   # run every 10 minutes