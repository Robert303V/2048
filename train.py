import numpy as np
from game import GameBoard
from agent import DQNAgent
import os

def get_reward(game, move_made):
    if not move_made:
        return -25  # Penalize heavily for making an invalid move
    
    if game.is_game_over():
        return -100 # Penalize for losing the game

    # Reward is the score gained in the last move
    return game.score

def train():
    episodes = 200 # Reduced for a quicker training cycle
    batch_size = 128
    
    game = GameBoard()
    state_shape = game.get_state().shape
    agent = DQNAgent(state_shape)
    
    if not os.path.exists('models'):
        os.makedirs('models')

    for e in range(episodes):
        game.reset()
        
        # Normalize initial state
        max_val = np.max(game.get_state())
        if max_val == 0: max_val = 1
        state = game.get_state() / max_val
        
        total_reward = 0
        last_score = 0
        
        for time in range(1000): # Max steps per episode
            action = agent.act(state)
            
            moves = ['up', 'down', 'left', 'right']
            move_made = game.move(moves[action])
            
            current_score = game.score
            reward = current_score - last_score
            last_score = current_score

            done = game.is_game_over()
            
            # Normalize next state
            next_state = game.get_state()
            max_val = np.max(next_state)
            if max_val == 0: max_val = 1
            next_state_normalized = next_state / max_val
            
            agent.remember(state, action, reward, next_state_normalized, done)
            
            state = next_state_normalized
            total_reward += reward
            
            if done:
                break
        
        print(f"Episode: {e+1}/{episodes}, Score: {game.score}, Total Reward: {total_reward}, Epsilon: {agent.epsilon:.2f}")
        
        agent.replay(batch_size)
        
        if (e + 1) % 50 == 0:
            agent.save(f"models/2048-dqn-{e+1}.keras")

    print("Training finished.")
    agent.save("models/2048-dqn-final.keras")

if __name__ == '__main__':
    train()
