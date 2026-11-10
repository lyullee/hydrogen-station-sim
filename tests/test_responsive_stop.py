import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from h2station import api
from h2station.simulation_clock import SimulationClock, SimulationStopped


def test_stop_wakes_long_realtime_wait():
    clock = SimulationClock(.5)
    clock.pace(0)
    entered = Event()
    def pace():
        entered.set()
        clock.pace(60)  # Would otherwise wait two minutes.
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(pace)
        assert entered.wait(1)
        start = time.monotonic()
        clock.cancel()
        with pytest.raises(SimulationStopped):
            future.result(timeout=1)
        assert time.monotonic() - start < .5


def test_cancel_queued_job_does_not_initialize_solver(monkeypatch):
    pending = []
    monkeypatch.setattr(api._executor, 'submit', lambda *args: pending.append(args))
    monkeypatch.setattr(api, 'build_reference_scenario', lambda *args: pytest.fail('cancelled job initialized'))
    with TestClient(api.app) as client:
        job_id = client.post('/api/simulations', json={'continuous': True}).json()['id']
        assert client.post(f'/api/simulations/{job_id}/stop').json()['status'] == 'stopping'
        fn, *args = pending.pop()
        fn(*args)
        assert client.get(f'/api/simulations/{job_id}').json()['stopped'] is True
        assert client.get(f'/api/simulations/{job_id}/result').json()['series']['time_s'] == []


def test_solver_rhs_observes_cancellation_before_next_derivative(monkeypatch):
    from h2station import safe_operation
    from h2station.scenario import ReferenceScenario, build_reference_scenario
    from h2station.risk.runtime_backend import UnavailableHyRAMBackend
    clock = SimulationClock()
    built = build_reference_scenario(ReferenceScenario(), UnavailableHyRAMBackend())
    called = []
    def interrupted_solver(rhs, interval, vector, **kwargs):
        called.append(True)
        clock.cancel()
        rhs(interval[0], vector)
        pytest.fail('solver continued after cancellation')
    monkeypatch.setattr(safe_operation, 'solve_ivp', interrupted_solver)
    with pytest.raises(SimulationStopped):
        built.simulator.simulate(built.initial_state, 1, .2,
                                 stop_callback=clock.check_cancelled)
    assert called


@pytest.mark.parametrize('fire', [False, True])
def test_running_stop_completes_and_commits_no_more_frames(fire):
    with TestClient(api.app) as client:
        payload = {'continuous': True, 'duration_s': 10, 'control_period_s': .2,
                   'process_settings': {}}
        if fire:
            payload['faults'] = [{'event_id':'stop-fire','kind':'external-fire',
                                  'target':'cascade.low','start_time_s':0,'magnitude':1,
                                  'external_temperature_c':800,'heat_transfer_ua_w_k':200}]
        response = client.post('/api/simulations', json=payload)
        assert response.status_code == 202, response.text
        job_id = response.json()['id']
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if len(client.get(f'/api/simulations/{job_id}/frames').json()['frames']) >= 3:
                    break
                time.sleep(.05)
            else:
                pytest.fail('simulation did not start')
            start = time.monotonic()
            client.post(f'/api/simulations/{job_id}/stop')
            while time.monotonic() - start < 2:
                status = client.get(f'/api/simulations/{job_id}').json()
                if status['status'] in ('complete','failed'):
                    break
                time.sleep(.02)
            assert status['status'] == 'complete', status
            elapsed = time.monotonic() - start
            print(f'fire={fire}: stop={elapsed:.3f}s')
            assert elapsed < 1.5
            frames = client.get(f'/api/simulations/{job_id}/frames').json()['frames']
            time.sleep(.2)
            assert client.get(f'/api/simulations/{job_id}/frames').json()['frames'] == frames
            result = client.get(f'/api/simulations/{job_id}/result').json()
            assert result['series']['time_s'] == [f['time_s'] for f in frames]
        finally:
            client.post(f'/api/simulations/{job_id}/stop')
