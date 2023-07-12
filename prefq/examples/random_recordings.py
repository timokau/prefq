"Generate recordings of random actions in gym environments." ""

import gym


def generate_random_episode_recordings(env_name, video_folder, num_episodes):
    """Generate recordings of random actions in gym environments."""
    env = gym.make(env_name, render_mode="rgb_array")
    env = gym.wrappers.RecordVideo(
        env, video_folder=video_folder, episode_trigger=lambda _: True
    )

    for _ in range(num_episodes):
        # Run a random episode until termination
        _observation, _info = env.reset()
        while True:
            # print("Step")
            # Sample an action
            action = env.action_space.sample()
            # Execute it, observe the results
            _observation, _reward, terminated, truncated, _info = env.step(action)

            if terminated or truncated:
                break
    print("Closing")
    env.close()


def main():
    """Run the script with default arguments"""
    generate_random_episode_recordings("LunarLander-v2", "./videos", 10)


if __name__ == "__main__":
    main()
