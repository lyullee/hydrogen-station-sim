/* Shared provider preference for the digital-twin assistants. */
(() => {
  const key = 'h2station.digital-twin.provider';
  const legacyKeys = [
    'h2station.main-assistant.provider',
    'h2station.sensor-assistant.provider',
    'h2station.saga.provider',
  ];
  const normalize = value => value === 'service_hub' ? 'service_hub' : 'groq';
  // This submission uses Groq. Migrate the old implicit Service Hub default once.
  if(localStorage.getItem('h2station.provider.groq-default-v1')!=='1'){
    localStorage.setItem(key,'groq');
    localStorage.setItem('h2station.provider.groq-default-v1','1');
  }
  function get() {
    const saved = localStorage.getItem(key);
    if (saved !== null) return normalize(saved);
    const legacy = legacyKeys.map(name => localStorage.getItem(name))
      .find(value => value === 'groq' || value === 'service_hub');
    const value = normalize(legacy);
    localStorage.setItem(key, value);
    return value;
  }
  function refresh() {
    document.querySelectorAll('.digital-twin-provider').forEach(select => {
      select.value = get();
    });
  }
  function set(value) {
    localStorage.setItem(key, normalize(value));
    refresh();
  }
  window.digitalTwinProvider = { get, set };
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) refresh();
  });
})();
