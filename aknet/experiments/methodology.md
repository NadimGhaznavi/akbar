# Experiment Methodology

This page describes how experiments are run.

Akbar submits a learning rate, initial epsilon, and epsilon decay baseline.

- Each hyperparameter expands into a lower, baseline, and higher value.
- The Cartesian product produces 27 hyperparameter configurations.
- Every configuration is used to run a **simulation** with the fixed seed 1970.
- Every simulation runs for exactly 1500 epochs.
- Training occurs once at the end of each epoch using one complete replay batch;
  there are no per-move training updates.
- Episode transitions are divided into fixed-size batches working backward from
  the terminal move. Any incomplete leading chunk is discarded.
- The complete experiment contains 27 separately persisted simulation results.
- A completed planned experiment is evaluated against its predeclared rationale
  and success criterion before the next experiment is proposed.
- Evaluations persist a `pass`, `fail`, or `inconclusive` verdict and a
  one-paragraph conclusion based on complete population-level evidence.
- The fixed seed and deterministic execution make an exact repeated configuration normally redundant.
- A deliberate duplicate requires a specific duplicate experiment reason.

- [Planning workflow](/experiments/workflow)
- [Writing rationales and duplicate reasons](/experiments/writing)
- [Data discipline](/data/discipline)
