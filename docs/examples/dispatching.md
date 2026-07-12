# Dispatching

[`examples/tutorial/dispatching/simple_dispatching_example.py`](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/tutorial/dispatching/simple_dispatching_example.py)
is **interactive**: it parses a small activity-network specification, dispatches activities as
their earliest-start time arrives, and lets you finish them by hand from the terminal, while a
live Gantt view (`metacsp.viz`) tracks progress.

```bash
python examples/tutorial/dispatching/simple_dispatching_example.py
```

A [`ConstraintNetworkAnimator`](../api/sensing.md) is created over the parsed
[`ActivityNetworkSolver`](../api/multi.activity.md), ticking every 100ms, and a
[`DispatchingFunction`](../api/dispatching.md) is registered per component:

```python
ans = ActivityNetworkSolver(origin, origin + 1000000)
cn = parsing.load_specification(str(_SPECIFICATION_FILE))
ans.add_constraints(*cn.get_constraints())

animator = ConstraintNetworkAnimator(ans, 100)
animator.add_dispatching_functions(df_mir, df_ur)
```

The custom `_PrintingDispatchingFunction` just prints when an activity starts:

```python
class _PrintingDispatchingFunction(DispatchingFunction):
    def dispatch(self, act: SymbolicVariableActivity) -> None:
        print(f"{act.component} starts executing {act.symbols[0]}")
```

Once running, the script prints the currently-started activities (one line per activity,
numbered) and prompts:

```
Executing activities (press <enter> to refresh list):
0: <activity>
1: <activity>
--
Please enter activity to finish:
```

- Press **Enter** with no input to just refresh the list (activities the dispatcher started
  since the last prompt will appear).
- Type an activity's **index number** (e.g. `0`) and press Enter to call
  `DispatchingFunction.finish` on it — this moves it to FINISHING, then FINISHED, freeing up
  whatever it was blocking.
- **Ctrl-D** (EOF) exits the loop and tears down the animator and viewer cleanly.

See [Sensing and dispatching](../concepts/sensing-and-dispatching.md) for the PLANNED → STARTED
→ FINISHING → FINISHED lifecycle this drives.
