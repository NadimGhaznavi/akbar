# Experiment Methodology

Akbar submits a learning rate, initial epsilon, and epsilon decay baseline.

- Each hyperparameter expands into a lower, baseline, and higher value.
- The Cartesian product produces 27 hyperparameter configurations.
- Every configuration runs with seeds 1970, 1971, and 1972.
- Every simulation runs for exactly 1500 epochs.
- The complete experiment contains 81 separately persisted simulation results.
- Fixed seeds and deterministic execution make an exact repeated configuration normally redundant.
- A deliberate duplicate requires a specific duplicate experiment reason.

- [Planning workflow](/experiments/workflow)
- [Writing rationales and duplicate reasons](/experiments/writing)
- [Data discipline](/data/discipline)
