import time
from fastapi.testclient import TestClient
from h2station.api import app


def test_fire_cooling_failure_off_and_incident_end_share_frame_state():
    with TestClient(app) as client:
        payload={'continuous':True,'duration_s':10,'control_period_s':.2,'speed_multiplier':5,
                 'process_settings':{},'faults':[{'event_id':'visual-fire','kind':'external-fire',
                 'target':'cascade.low','start_time_s':0,'external_temperature_c':800,'heat_transfer_ua_w_k':200}]}
        response=client.post('/api/simulations',json=payload)
        assert response.status_code==202,response.text
        prefix='/api/simulations/'+response.json()['id']
        def wait(predicate):
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                rows=client.get(prefix+'/frames').json()['frames']
                if rows and predicate(rows[-1]):return rows[-1]
                time.sleep(.03)
            raise AssertionError('Expected response state was not published')
        def action(kind,target):
            r=client.post(prefix+'/safety/actions',json={'kind':kind,'target':target})
            assert r.status_code==200,r.text
            return r.json()['action']
        try:
            wait(lambda f:'external-fire:cascade.low' in f['active_faults'])
            assert client.get(prefix+'/safety').json()['active_incidents'][0]['event_id']=='visual-fire'
            action('cooling.on','low')
            frame=wait(lambda f:f['virtual_safety']['cooling']['low']['running'])
            assert 'external-fire:cascade.low' in frame['active_faults']
            action('cooling.off','low')
            wait(lambda f:not f['virtual_safety']['cooling']['low']['running'])
            r=client.put(prefix+'/safety/faults/cooling.low',json={'fault':'failure'})
            assert r.status_code==200,r.text
            assert action('cooling.on','low')['status']=='failed'
            wait(lambda f:f['virtual_safety']['cooling']['low']['fault'] and not f['virtual_safety']['cooling']['low']['running'])
            assert client.delete(prefix+'/faults/visual-fire').status_code==202
            wait(lambda f:'external-fire:cascade.low' not in f['active_faults'])
            assert client.get(prefix+'/safety').json()['active_incidents']==[]
        finally:
            client.post(prefix+'/stop')
