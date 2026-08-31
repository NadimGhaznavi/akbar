# Epsilon Decay

Epsilon decay is multiplied into epsilon after each epoch and controls how quickly random exploration decreases during training.

- Values closer to one preserve exploration for longer.
- Smaller values move toward exploitation more quickly.
- The experiment varies the decay amount by five percent rather than varying epsilon decay directly, preserving useful resolution near one.
- Interpret epsilon decay together with initial epsilon and the fixed 1500-epoch duration.

- [Learning rate](/snake-lab/learning-rate)
- [Initial epsilon](/snake-lab/initial-epsilon)
- [Return to the AI Snake Lab](/snake-lab/)
