"""Watcher simples em polling para a pasta /data/bronze.
Verifica mudanças nos timestamps dos arquivos e dispara o pipeline
executando `python /app/main.py` dentro do mesmo container.

Não requer inotify (funciona em ambientes sem inotify-tools).
"""
import time
import os
import subprocess
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BRONZE_DIR = os.getenv('BRONZE_DIR', '/data/bronze')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))


def snapshot(dirpath):
    state = {}
    try:
        for fn in os.listdir(dirpath):
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
                state[fn] = (st.st_mtime, st.st_size)
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        return {}
    return state


def changed(a, b):
    return a != b


def run_pipeline():
    logger.info('Change detected — running pipeline...')
    try:
        # Executar main.py diretamente
        subprocess.run(['python', '/app/main.py'], check=True)
        logger.info('Pipeline finished successfully')
    except subprocess.CalledProcessError as e:
        logger.error(f'Pipeline failed: {e}')


def main():
    logger.info(f'Watcher started: monitoring {BRONZE_DIR} (poll {POLL_INTERVAL}s)')
    last = snapshot(BRONZE_DIR)
    while True:
        time.sleep(POLL_INTERVAL)
        cur = snapshot(BRONZE_DIR)
        if changed(cur, last):
            run_pipeline()
            last = cur


if __name__ == '__main__':
    main()
