"""Run every remote preset through its complete default event window."""
import json
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import time

import numpy as np

from h2station.api import SimulationInput
from h2station.hazop.runtime import HazopMonitor
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def validate(preset):
    start = time.monotonic()
    record = {'id': preset['id'], 'title': preset['title']}
    try:
        request = SimulationInput(duration_s=25, control_period_s=.2, faults=preset['faults'])
        built = build_reference_scenario(
            ReferenceScenario(fault_events=tuple(f.to_event() for f in request.faults)),
            UnavailableHyRAMBackend(),
        )
        built.simulator.hazop_monitor = HazopMonitor(virtual_detectors=True)
        trajectory = built.simulator.simulate(built.initial_state, 25, .2)
        assert np.isfinite(trajectory.states).all()
        assert abs(float(trajectory.time_s[-1]) - 25) < 1e-6
        record.update(status='passed', samples=len(trajectory.time_s))
    except Exception as error:
        record.update(status='failed', error=f'{type(error).__name__}: {error}')
    record['elapsed_s'] = round(time.monotonic() - start, 2)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Reuse passed records only if model and catalog inputs are unchanged.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / 'web/scenarios.json').read_text(encoding='utf-8'))
    path = root / 'data/remote-full-window-validation.json'
    report = json.loads(path.read_text(encoding='utf-8')) if args.resume and path.exists() else []
    report = [record for record in report if record['status'] == 'passed']
    completed = {record['id'] for record in report}
    with ProcessPoolExecutor(max_workers=6) as executor:
        pending = [executor.submit(validate, preset) for preset in catalog['scenarios'] if preset['id'] not in completed]
        for future in as_completed(pending):
            record = future.result()
            report.append(record)
            print(record['id'], record['status'], record.get('error', ''), flush=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    raise SystemExit(any(item['status'] != 'passed' for item in report))


if __name__ == '__main__':
    main()
