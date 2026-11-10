import time
from fastapi.testclient import TestClient
from h2station.api import app, _process_runtimes

def test_approved_restart_resets_plc_on_next_sample_and_keeps_running():
    with TestClient(app) as client:
        r=client.post('/api/simulations',json={'continuous':True,'duration_s':10,'control_period_s':.2,'speed_multiplier':10,'process_settings':{}})
        assert r.status_code==202
        job=r.json()['id'];url='/api/simulations/'+job
        def wait(predicate):
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                result=client.get(url+'/frames').json()
                assert result['job']['status']!='failed',result['job']
                if result['frames'] and predicate(result['frames'][-1]):return result['frames'][-1]
                time.sleep(.03)
            raise AssertionError('Frame condition not reached')
        try:
            wait(lambda f:True)
            assert client.post(url+'/safety/actions',json={'kind':'esd.trip','target':'station'}).status_code==200
            wait(lambda f:f['esd'])
            safety=_process_runtimes[job].safety
            # Recovery procedures themselves have separate actuator tests;
            # this fixture exercises the previously broken API-to-PLC handoff.
            safety.recovery={key:True for key in safety.recovery}
            r=client.post(url+'/safety/actions',json={'kind':'restart.approve','target':'station'})
            assert r.status_code==200,r.text
            assert r.json()['action']['status']=='commanded'
            frame=wait(lambda f:not f['esd'] and f['virtual_safety']['recovery_approved'])
            wait(lambda f:f['sequence']>=frame['sequence']+10)
            assert client.get(url).json()['status']=='running'
        finally:client.post(url+'/stop')
