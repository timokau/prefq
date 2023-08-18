# This example is taken from [1] (MIT licensed). It does not currently use PrefQ.
# It only serves to show that the `imitation` dependency is working.
# [1] https://github.com/HumanCompatibleAI/imitation/blob/19c7f35d7cac97e623f352d367fa384f5f3bb465/docs/algorithms/preference_comparisons.rst

# Disable formatting and linters so we can keep the example as close to the original as possible for now.
# fmt: off
# pylint: skip-file
import numpy as np
from imitation.algorithms import preference_comparisons
from imitation.policies.base import FeedForward32Policy, NormalizeFeaturesExtractor
from imitation.rewards.reward_nets import BasicRewardNet
from imitation.rewards.reward_wrapper import RewardVecEnvWrapper
from imitation.util.networks import RunningNorm
from imitation.util.util import make_vec_env
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.ppo import MlpPolicy

rng = np.random.default_rng(0)

venv = make_vec_env("Pendulum-v1", rng=rng)

reward_net = BasicRewardNet(
    venv.observation_space, venv.action_space, normalize_input_layer=RunningNorm,
)

fragmenter = preference_comparisons.RandomFragmenter(warning_threshold=0, rng=rng)
gatherer = preference_comparisons.SyntheticGatherer(rng=rng)
preference_model = preference_comparisons.PreferenceModel(reward_net)
reward_trainer = preference_comparisons.BasicRewardTrainer(
    preference_model=preference_model,
    loss=preference_comparisons.CrossEntropyRewardLoss(),
    epochs=3,
    rng=rng,
)

agent = PPO(
    policy=FeedForward32Policy,
    policy_kwargs=dict(
        features_extractor_class=NormalizeFeaturesExtractor,
        features_extractor_kwargs=dict(normalize_class=RunningNorm),
    ),
    env=venv,
    n_steps=2048 // venv.num_envs,
)

trajectory_generator = preference_comparisons.AgentTrainer(
    algorithm=agent,
    reward_fn=reward_net,
    venv=venv,
    exploration_frac=0.0,
    rng=rng,
)

querent = preference_comparisons.PreferenceQuerent()
pref_comparisons = preference_comparisons.PreferenceComparisons(
    trajectory_generator,
    reward_net,
    num_iterations=5,
    fragmenter=fragmenter,
    preference_querent=querent,
    preference_gatherer=gatherer,
    reward_trainer=reward_trainer,
    initial_epoch_multiplier=1,
)
pref_comparisons.train(total_timesteps=5_000, total_comparisons=200)

reward, _ = evaluate_policy(agent.policy, venv, 10)
print("Reward:", reward)
