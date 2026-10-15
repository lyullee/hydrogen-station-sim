// Use Epic's public frontend APIs. The desktop pilot has no XR controls.
document.body.onload = function () {
  const api = window['epicgames-frontend'];
  if (!api) {document.body.textContent='Pixel Streaming 프런트엔드를 먼저 빌드해 주세요.';return;}
  const styles = new api.PixelStreamingApplicationStyle(); styles.applyStyleSheet();
  const config = new api.Config({useUrlParams:true});
  const stream = new api.PixelStreaming(config);
  const app = new api.Application({stream,
    settingsPanelConfig:{isEnabled:false,
      visibilityButtonConfig:{creationMode:api.UIElementCreationMode.Disable}},
    statsPanelConfig:{isEnabled:false,
      visibilityButtonConfig:{creationMode:api.UIElementCreationMode.Disable}},
    fullScreenControlsConfig:{creationMode:api.UIElementCreationMode.Disable},
    xrControlsConfig:{creationMode:api.UIElementCreationMode.Disable},
    videoQpIndicatorConfig:{disableIndicator:true},
    onColorModeChanged:light=>styles.setColorMode(light)});
  document.body.appendChild(app.rootElement);
  window.pixelStreaming=stream;
};
