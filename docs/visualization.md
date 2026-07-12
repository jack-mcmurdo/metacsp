# Visualization

`metacsp.viz` (dearpygui) is being replaced by a web-based frontend. The stable contract for
any consumer — the in-scope live viewer or a future one — is the JSON snapshot/delta protocol
documented in [Visualization protocol](VIZ.md) and implemented by
[`metacsp.serialization`](api/serialization.md); see also [`metacsp.viz`](api/viz.md) for the
current dearpygui-based implementation.

!!! note
    This page will be rewritten once the web-based viewer lands. It deliberately does not
    document dearpygui workflows in depth — see [Visualization protocol](VIZ.md) for the
    protocol both the current and future viewers are built on.
