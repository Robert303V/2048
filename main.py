import pygame
import sys
from game import GameBoard
from gui import GameGUI
from agent import ExpectimaxAgent

SPEEDS = [
    ("Normal", 70),
    ("Fast", 20),
    ("Turbo", 0),
]


def execute_move(game, gui, direction, animate=True, duration=0.095):
    """Executes a move, triggers smooth slide animation, plays sound, and checks milestones."""
    if gui.is_animating():
        gui.finish_animation()

    if game.move(direction):
        if animate and duration > 0 and game.last_transitions:
            gui.start_animation(game.last_transitions, game.last_spawn, duration=duration)

        if game.just_unlocked_milestone:
            gui.trigger_milestone(game.just_unlocked_milestone)
        elif game.highest_tile_merged > 0:
            gui.sound.play_merge(game.highest_tile_merged)
        else:
            gui.sound.play_slide()

        if game.is_game_over():
            gui.sound.play_game_over()
        return True
    return False


def main():
    game = GameBoard()
    gui = GameGUI(game)
    agent = ExpectimaxAgent()

    speed_index = 0
    running = True
    is_bot_running = False
    clock = pygame.time.Clock()
    last_bot_move_time = 0

    gui.stats.increment_games()

    while running:
        current_time = pygame.time.get_ticks()
        speed_name, speed_delay = SPEEDS[speed_index]

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # --- Mouse Click Detection ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if gui.bot_btn_rect.collidepoint(pos):
                    is_bot_running = not is_bot_running
                elif gui.step_btn_rect.collidepoint(pos):
                    # Single step with Bot
                    if not game.is_game_over():
                        is_bot_running = False
                        best_move = agent.get_best_move(game.get_state())
                        if best_move:
                            execute_move(game, gui, best_move, animate=True, duration=0.095)
                elif gui.undo_btn_rect.collidepoint(pos):
                    is_bot_running = False
                    gui.finish_animation()
                    game.undo()
                elif gui.speed_btn_rect.collidepoint(pos):
                    speed_index = (speed_index + 1) % len(SPEEDS)
                elif gui.reset_btn_rect.collidepoint(pos):
                    gui.finish_animation()
                    game.reset()
                    gui.stats.increment_games()
                    is_bot_running = False
                elif gui.theme_btn_rect.collidepoint(pos):
                    gui.toggle_theme()
                elif gui.sound_btn_rect.collidepoint(pos):
                    gui.sound.toggle_mute()

            # --- Keyboard Input ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    is_bot_running = not is_bot_running
                elif event.key == pygame.K_n:
                    # Single step with Bot
                    if not game.is_game_over():
                        is_bot_running = False
                        best_move = agent.get_best_move(game.get_state())
                        if best_move:
                            execute_move(game, gui, best_move, animate=True, duration=0.095)
                elif event.key == pygame.K_u:
                    is_bot_running = False
                    gui.finish_animation()
                    game.undo()
                elif event.key == pygame.K_s:
                    speed_index = (speed_index + 1) % len(SPEEDS)
                elif event.key == pygame.K_t:
                    gui.toggle_theme()
                elif event.key == pygame.K_m:
                    gui.sound.toggle_mute()
                elif event.key == pygame.K_r:
                    gui.finish_animation()
                    game.reset()
                    gui.stats.increment_games()
                    is_bot_running = False

                # Manual player moves only when Bot is paused
                if not is_bot_running and not game.is_game_over():
                    if event.key == pygame.K_UP:
                        execute_move(game, gui, 'up', animate=True, duration=0.095)
                    elif event.key == pygame.K_DOWN:
                        execute_move(game, gui, 'down', animate=True, duration=0.095)
                    elif event.key == pygame.K_LEFT:
                        execute_move(game, gui, 'left', animate=True, duration=0.095)
                    elif event.key == pygame.K_RIGHT:
                        execute_move(game, gui, 'right', animate=True, duration=0.095)

        # --- Bot Move Execution ---
        if is_bot_running and not game.is_game_over():
            if current_time - last_bot_move_time >= speed_delay:
                best_move = agent.get_best_move(game.get_state())
                if best_move:
                    # In Normal mode (delay = 70ms), animate with a snappy 40ms slide within the delay
                    # In Fast or Turbo mode, disable animation completely to guarantee maximum speed!
                    bot_animate = (speed_name == "Normal")
                    bot_duration = 0.040 if bot_animate else 0.0
                    execute_move(game, gui, best_move, animate=bot_animate, duration=bot_duration)
                else:
                    is_bot_running = False
                last_bot_move_time = pygame.time.get_ticks()

        # Update Display
        gui.update_display(is_bot_running, speed_name)
        clock.tick(60)

    gui.stats.flush()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
