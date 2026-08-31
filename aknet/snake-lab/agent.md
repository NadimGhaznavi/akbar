# Snake Agent

Each epoch is one complete Snake game.

## Observations

- Danger straight, right, and left
- Current movement direction
- Whether food is left, right, above, or below the head
- Eleven binary features in total

## Actions

- Continue straight
- Turn right
- Turn left

## Rewards

- Positive ten for eating food
- Negative ten for collision or exceeding the move limit
- Positive one for moving closer to food
- Negative one for moving farther from food

## Learning

- One linear eleven-input, three-output Q-function with bias
- No hidden layers and no separate target network
- Epsilon-greedy action selection
- One-step temporal-difference targets
- Immediate transition training and one replay-memory batch after each game
- Fresh model and replay memory for every simulation

- [AI Snake Lab](/snake-lab/)
- [Experiment methodology](/experiments/methodology)
