#!/usr/bin/env python3
"""Run the supported installer wait command while servicing scoped UPI CSRs."""
import pathlib
import subprocess
import sys
import time

installer, directory, phase, oc, nodes = sys.argv[1:]
helper = pathlib.Path(__file__).with_name('approve-node-csrs.py')
log = pathlib.Path(directory) / (phase + '-wait.log')
with log.open('a') as output:
    process = subprocess.Popen([installer, '--dir', directory, 'wait-for', phase],
                               stdout=output, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 7200
        while process.poll() is None:
            subprocess.run([sys.executable, str(helper), oc, nodes], check=False, timeout=120)
            if time.monotonic() >= deadline:
                raise TimeoutError(f'{phase}: exceeded two hours; see {log}')
            time.sleep(10)
        if process.returncode:
            print(log.read_text()[-12000:], file=sys.stderr)
        sys.exit(process.returncode)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
