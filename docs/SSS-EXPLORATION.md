# Explore skills and BW workflows with S³

BW imports the optional Skills³ package. S³ owns definitions, independent scoring,
practice and reports. BW keeps its task ledger, tool grants and recovery.

```sh
python -m branchwrite skills
python -m branchwrite skills explore doctor
python -m branchwrite skills workflows list
python -m branchwrite skills workflows show blender
python -m branchwrite skills workflows show cad-plate
```

The [S³ start guide](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/START-HERE.md)
and [operator handoff](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/OPERATOR-HANDOFF.md)
give a checked reference walkthrough suitable for a smaller exploration model.
[Domain recipes](https://github.com/CC-David-CC/sss/blob/feat/foundations-20261023/docs/BW-WORKFLOWS.md)
cover Blender, build123d, PDFs, writing, websites, remote administration and
follow-up work. They preserve BW's existing execution/checker boundaries and
version-scoped historical evidence. New per-cell S³ qualifications are pending.

PCC accepts explicit schema-2 multi-turn owned lessons. The existing
`branchwrite lesson submit FILE` path queues them; single and batch updates
remain explicit. Target policy selects verified thinking/actions/answers or
actions/answers only. Excluding thought labels does not detach earlier context
from backprop. Inference thinking is configured independently.

Reference examples and tiny CPU fixture updates do not train or qualify Wen.
`skills legacy` and `skills --active FILE` retain the older active-tree view.
Saved BW tasks retain their original runtime/configuration. Graph/recipe
inspection does not migrate tasks, authorize tools, start a GPU or promote weights.

CPU checkpoint: [dated validation](../validation/foundations-20261023/README.md).
