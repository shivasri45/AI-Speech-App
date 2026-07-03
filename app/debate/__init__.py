"""Group debate feature.

Package marker for the multi-participant debate feature. Establishes the
`app.debate` import root used by schemas, scoring, service, room manager,
and route modules. This package reuses the existing analysis pipeline via
`app.debate.service.analyze_turn_audio` and does not duplicate any
pronunciation or fluency logic.
"""
