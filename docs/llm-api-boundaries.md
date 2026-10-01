# LLM API boundaries

The three user surfaces are independent contracts. New code must not route one surface through another surface's endpoint, prompt builder, browser setting, or conversation state.

| Surface | Browser API | Port 8090 downstream API | Prompt ownership | Provider setting |
| --- | --- | --- | --- | --- |
| Main digital-twin chat | `/api/simulations/{job}/assistants/main[/stream]` | `/api/integrations/digital-twin/main[/stream]` | Main operations question or automatic alarm summary | `h2station.main-assistant.provider` |
| Selected-sensor analysis | `/api/simulations/{job}/assistants/sensors/{tag}[/stream]` | `/api/integrations/digital-twin/sensor[/stream]` | One selected sensor and its local process context | `h2station.sensor-assistant.provider` |
| Standalone SAGA on 8090 | `/api/chat[/stream]` | None | SAGA RAG, document search, review, and its own conversation | SAGA server/UI configuration |

The main and sensor integration APIs use a single direct completion. They never invoke the standalone SAGA RAG/review pipeline and never modify its conversation or model configuration. The main assistant receives main-chat history; the sensor assistant does not receive it.

`request_kind=user_query` requires the model to answer the user's current question or instruction first. `request_kind=automatic_analysis` is reserved for automatic status and alarm reporting. Consequence calculations remain in the digital-twin server and are supplied as calculated context before either assistant is called.

The older `/saga-analysis/direct`, `/sensors/{tag}/analyze/direct`, and `/api/digital-twin/chat/direct` routes remain compatibility endpoints. Browser code must use the isolated routes above.
