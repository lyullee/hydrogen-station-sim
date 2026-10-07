"""Build the reviewed remote scenario catalog from implemented fault kinds and HAZOP tags."""
from pathlib import Path
import json
from h2station.api import SimulationInput
from h2station.hazop.database import load_catalog
from h2station.hazop.mapping import MODEL_BINDINGS

ROOT=Path(__file__).resolve().parents[1]
physical=[('cascade.low','저압 저장뱅크'),('cascade.medium','중압 저장뱅크'),('cascade.high','고압 저장뱅크'),('dispenser.hose','1번 충전호스'),('dispenser_2.hose','2번 충전호스'),('vehicle.tank','1번 차량탱크'),('vehicle_2.tank','2번 차량탱크'),('compressor','압축기 연결부'),('header','공급 헤더')]
lines=physical[3:5]
core=physical[:7]
catalog=load_catalog()
sensors=[{'value':s['sensor_id'],'label':f"{s['sensor_id']} · {s['node_id']} ({s['단위']})",'unit':s['단위'],'location':s['설치_측정위치']} for s in catalog['sensors'] if s['sensor_id'] in MODEL_BINDINGS]
choices=lambda values:[{'value':key,'label':label} for key,label in values]
kinds=[]
def kind(key,label,targets,fields,note):
    kinds.append({'id':key,'label':label,'targets':targets,'fields':fields,'note':note})
kind('hydrogen-leak','수소 누출',choices(physical),['leak_diameter_mm','indoor','ignited','enclosure_volume_m3','enclosure_vent_area_m2'],'누출 질량·에너지를 재고에서 차감합니다. 실내·즉시점화를 함께 선택하면 검증된 환기식 밀폐공간 압력피크 모델을 계산합니다.')
kind('external-fire','외부 화재',choices(physical),['external_temperature_c','heat_transfer_ua_w_k'],'열원과 설비의 온도차 및 UA로 열전달을 계산합니다. 자동 점화·연소 전파 모델은 아닙니다.')
kind('pressure-disturbance','공정 압력 상승·저하',choices(physical),['magnitude','rate_s'],'MPa 변화량에 따른 질량 유입·유출을 적용합니다. 응답시간은 질량 변화 속도를 정합니다.')
kind('temperature-disturbance','외부 가열·냉각',choices(physical),['external_temperature_c','heat_transfer_ua_w_k'],'가열·냉각 경계와 공정 사이의 열전달로 온도가 변합니다.')
kind('pipe-restriction','배관·PCV 부분 막힘',choices(lines+[('dispenser.pcv','1번 PCV'),('dispenser_2.pcv','2번 PCV')]),['magnitude'],'유효 개방률 1은 정상, 0은 완전 폐쇄입니다.')
kind('check-valve-failure','체크밸브 고장',choices(lines),[],'역방향 유동을 허용합니다. 실제 역류는 해당 시점의 압력차에 따라 결정됩니다.')
kind('pcv-seat-leak','PCV 시트 누설',choices([('dispenser.pcv','1번 PCV'),('dispenser_2.pcv','2번 PCV'),('pcv','두 라인 공통 PCV')]),['magnitude'],'닫힘 명령 후에도 남는 유효 개방률입니다. 0 입력 시 기본 시트 누설률 3%를 적용합니다.')
for key,label in [('pcv-stuck-open','PCV 열린 고착'),('pcv-stuck-closed','PCV 닫힌 고착')]:kind(key,label,choices([('pcv','두 라인 공통 PCV')]),[],'현재 모델은 두 충전 라인에 공통 고착 명령을 적용합니다.')
for key,label in [('cascade-valve-stuck-open','캐스케이드 밸브 열린 고착'),('cascade-valve-stuck-closed','캐스케이드 밸브 닫힌 고착')]:kind(key,label,choices([('cascade','공통 캐스케이드 밸브')]),[],'두 충전 라인의 뱅크 전환 밸브에 공통 적용됩니다.')
kind('precooler-loss','예냉 성능 저하',choices([('precooler','두 라인 예냉기')]),['magnitude'],'잔존 냉각 용량을 0~1로 설정합니다. 0은 냉각 상실입니다.')
kind('compressor-trip','압축기 정지',choices([('compressor','압축기')]),[],'저장뱅크 재충전을 중지합니다.')
kind('emergency-stop','비상 정지 요청',choices([('station','전체 충전소')]),[],'기존 안전 PLC에 ESD 요청을 전달합니다. 종료 후에도 ESD 래치는 유지됩니다.')
kind('sensor-bias','센서 편향',sensors,['magnitude'],'표시 단위의 편향값을 HAZOP 진단 신호에 더합니다. 물리 공정값과 기존 PLC 입력은 바꾸지 않습니다.')
kind('sensor-freeze','센서 값 고정',sensors,[],'사고 시작 시점의 HAZOP 진단값을 유지합니다. 물리 공정은 계속 계산됩니다.')
scenarios=[]
def fault(kind,target,**params):return {'kind':kind,'target':target,'start_time_s':5.0,'end_time_s':20.0,**params}
def add(category,title,description,*faults):
    sid=f'{category}-{sum(s["category"]==category for s in scenarios)+1:02d}'
    for i,f in enumerate(faults):f['event_id']=sid+f'-{i+1}'
    SimulationInput(duration_s=30,faults=list(faults))
    scenarios.append({'id':sid,'category':category,'title':title,'description':description,'faults':list(faults)})
for target,label in physical:
    add('leak',label+' 수소 누출','5~20초 · 구경 0.2 mm · 누출 질량과 해당 구역 가스검지 신호 추적',fault('hydrogen-leak',target,leak_diameter_mm=.2))
for target,label in core:
    add('fire',label+' 외부 화재','5~20초 · 열원 800 °C · UA 1,000 W/K',fault('external-fire',target,external_temperature_c=800,heat_transfer_ua_w_k=1000))
for target,label in core:
    for mag,title in [(10,'압력 상승'),(-10,'압력 저하')]:
        add('pressure',label+' '+title,f'5~20초 · 변화량 {mag:+} MPa · 응답시간 30초',fault('pressure-disturbance',target,magnitude=mag,rate_s=30))
for target,label,temp in [('vehicle.tank','1번 차량탱크 가열',150),('vehicle_2.tank','2번 차량탱크 가열',150),('dispenser.hose','1번 호스 외부 냉각',-40),('dispenser_2.hose','2번 호스 외부 냉각',-40)]:
    add('thermal',label,f'5~20초 · 외부 경계 {temp} °C · UA 500 W/K',fault('temperature-disturbance',target,external_temperature_c=temp,heat_transfer_ua_w_k=500))
for target,label in lines+[('dispenser.pcv','1번 PCV'),('dispenser_2.pcv','2번 PCV')]:
    add('flow',label+' 부분 막힘','5~20초 · 유효 개방률 25%',fault('pipe-restriction',target,magnitude=.25))
for target,label in lines:
    add('flow',label+' 체크밸브 고장','5~20초 · 역류 방지 상실 · 압력차에 따른 유동 추적',fault('check-valve-failure',target))
add('equipment','1번 PCV 시트 누설','닫힘 명령 후 1번 PCV 유효 개방률 3% 유지',fault('pcv-seat-leak','dispenser.pcv',magnitude=.03))
for k in kinds:
    if k['id'] in ['pcv-stuck-open','pcv-stuck-closed','cascade-valve-stuck-open','cascade-valve-stuck-closed','compressor-trip','emergency-stop']:
        add('equipment',k['label'],k['note'],fault(k['id'],k['targets'][0]['value']))
for ratio,label in [(.25,'예냉 용량 75% 저하'),(0,'예냉 냉각 완전 상실')]:
    add('equipment',label,'5~20초 · 두 충전 라인 공통 예냉 성능 변경',fault('precooler-loss','precooler',magnitude=ratio))
for tag,label,bias in [('PT-1401','1번 차량 압력',90),('PT-1801','2번 차량 압력',90),('TT-1401','1번 차량 온도',70),('TT-1801','2번 차량 온도',70),('PT-0901','고압뱅크 압력',20),('FT-1301','1번 노즐 유량',-30)]:
    add('sensor',label+' 센서 편향',f'{tag} · 표시 단위 {bias:+} · 공정값과 진단값 비교',fault('sensor-bias',tag,magnitude=bias))
    add('sensor',label+' 센서 고정',f'{tag} · 5초의 진단값을 20초까지 유지',fault('sensor-freeze',tag))
add('compound','호스 누출 후 비상 정지','2번 호스 5초 누출 → 10초 ESD. 잔류 재고에서의 누출 확인',fault('hydrogen-leak','dispenser_2.hose',leak_diameter_mm=.3),fault('emergency-stop','station',start_time_s=10))
add('compound','두 호스 동시 누출','1·2번 충전호스 동시 0.2 mm 누출',fault('hydrogen-leak','dispenser.hose',leak_diameter_mm=.2),fault('hydrogen-leak','dispenser_2.hose',leak_diameter_mm=.2))
add('compound','저장뱅크 화재와 압축기 정지','고압뱅크 외부 화재 + 압축기 정지',fault('external-fire','cascade.high',external_temperature_c=800,heat_transfer_ua_w_k=1000),fault('compressor-trip','compressor'))
add('compound','예냉 상실과 차량 가열','예냉 냉각 상실 + 1번 차량 외부 가열',fault('precooler-loss','precooler',magnitude=0),fault('temperature-disturbance','vehicle.tank',external_temperature_c=150,heat_transfer_ua_w_k=500))
add('compound','저압 뱅크 저하와 호스 막힘','공급 압력 저하 + 1번 호스 개방률 25%',fault('pressure-disturbance','cascade.low',magnitude=-10,rate_s=30),fault('pipe-restriction','dispenser.hose',magnitude=.25))
add('compound','고압 뱅크 누출과 센서 고정','물리 누출과 PT-0901 진단 센서 고정을 비교',fault('hydrogen-leak','cascade.high',leak_diameter_mm=.2),fault('sensor-freeze','PT-0901'))
add('compound','2번 차량 가압과 체크밸브 고장','차량 가압 + 2번 호스 역류 허용. 역류 발생은 압력차에 의존',fault('pressure-disturbance','vehicle_2.tank',magnitude=10,rate_s=30),fault('check-valve-failure','dispenser_2.hose'))
add('compound','화재 노출 후 지연 누출','고압뱅크 5초 화재, 10초 누출을 각각 명시적으로 주입',fault('external-fire','cascade.high',external_temperature_c=800,heat_transfer_ua_w_k=1000),fault('hydrogen-leak','cascade.high',start_time_s=10,leak_diameter_mm=.2))
output={'version':'20261008-ignited-enclosure1','categories':[{'id':k,'label':v} for k,v in [('leak','누출'),('fire','외부 화재'),('pressure','압력'),('thermal','가열·냉각'),('flow','막힘·역류'),('equipment','설비 고장'),('sensor','센서 진단'),('compound','복합 사고')]],'kinds':kinds,'scenarios':scenarios}
(ROOT/'web/scenarios.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(scenarios)} scenarios / {len(kinds)} kinds / {len(sensors)} sensor targets')
