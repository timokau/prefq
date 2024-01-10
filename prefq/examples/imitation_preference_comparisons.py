"""
This module provides an example implementation for dynamic queries 
and integrating our PrefQ server into the imitation library.
"""

# Hyperparameters used in this file have been taken from
# https://github.com/HumanCompatibleAI/imitation/pull/771

# Disable formatting and linters so we can keep the example as close to the original as possible for now.
# fmt: off
# pylint: skip-file

import os
import pathlib
import tempfile
from typing import Optional, Sequence, Tuple

import numpy as np
from imitation.algorithms import preference_comparisons
from imitation.algorithms.preference_comparisons import (
    SynchronousHumanGatherer,
    write_fragment_video,
)
from imitation.data.types import TrajectoryWithRewPair
from imitation.data.wrappers import RenderImageInfoWrapper
from imitation.policies.base import FeedForward32Policy, NormalizeFeaturesExtractor
from imitation.rewards.reward_nets import BasicRewardNet
from imitation.util import logger as imit_logger
from imitation.util.networks import RunningNorm
from imitation.util.util import make_vec_env
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy

from prefq.query_client import QueryClient

SERVER_URL = "http://127.0.0.1:5000/"


class PrefqGatherer(SynchronousHumanGatherer):
    """
    Gatherer for synchronous communication with a flask webserver.

    Sends video pairs associated with a Query-ID to server.
    Then, in a blocking while loop waits for full evaluation of all queries.

    This class is a slightly modified version of the PrefCollectGatherer
    introduced in https://github.com/HumanCompatibleAI/imitation/pull/716
    """

    def __init__(
        self,
        video_dir: pathlib.Path = None,
        video_width: int = 500,
        video_height: int = 500,
        frames_per_second: int = 25,
        custom_logger: Optional[imit_logger.HierarchicalLogger] = None,
        rng: Optional[np.random.Generator] = None,
        server_url: str = None,
    ) -> None:
        super().__init__(custom_logger=custom_logger, rng=rng, video_dir=video_dir)
        self.video_dir = video_dir
        os.makedirs(video_dir, exist_ok=True)
        self.video_width = video_width
        self.video_height = video_height
        self.frames_per_second = frames_per_second
        self.server_url = server_url

    def gather(self) -> Tuple[Sequence[TrajectoryWithRewPair], np.ndarray]:
        """Iteratively sends video-pairs associated with a Query-ID to server."""

        query_client = QueryClient(self.server_url)

        for i, (query_id, query) in enumerate(self.pending_queries.items()):
            write_fragment_video(
                query[0],
                frames_per_second=self.frames_per_second,
                output_path=os.path.join(self.video_dir, f"{query_id}-left.webm"),
            )
            write_fragment_video(
                query[1],
                frames_per_second=self.frames_per_second,
                output_path=os.path.join(self.video_dir, f"{query_id}-right.webm"),
            )

            query_client.send_video_pair(query_id, f"{query_id}-left.webm", f"{query_id}-right.webm", self.video_dir)

        feedback_data = query_client.request_feedback()

        preferences = np.zeros(len(self.pending_queries), dtype=np.float32)
        for i, query_id in enumerate(self.pending_queries.keys()):
            # Order of queries and preferences must match, but the
            # server response is unordered due to:
            #   (1) The asynchronous nature feedback collection
            #       (multiple users can send feedback)
            #   (2) The nature of the flask.jsonify() function,
            #       that orders keys alphanumerically.
            #       This behavior can be turned off,
            #       but makes no sense due to (1)
            is_left_preferred = 1 if feedback_data[query_id] else 0
            preferences[i] = is_left_preferred

        print(f"\n\nPreferences:\n{np.vstack(preferences)}")

        queries = list(self.pending_queries.values())
        self.pending_queries.clear()

        return queries, preferences

rng = np.random.default_rng(0)
video_dir = tempfile.mkdtemp(prefix="videos_")

# By using the use_file_cache=True we avoid RAM overflow,
# enabeling us to run this example even with only 8GB RAM.
venv = make_vec_env(
    env_name="Pendulum-v1",
    rng=rng,
    post_wrappers=[
        lambda env, env_id: RenderImageInfoWrapper(env, use_file_cache=True)
    ],
    env_make_kwargs={"render_mode": "rgb_array"},
)


class EnvClosingContext:
    """Ensures that all trajectories will be deleted in case of an interruption."""

    def __init__(self, env):
        self.env = env

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        self.env.close()


with EnvClosingContext(venv):
    reward_net = BasicRewardNet(
        venv.observation_space,
        venv.action_space,
        normalize_input_layer=RunningNorm,
    )

    fragmenter = preference_comparisons.RandomFragmenter(warning_threshold=0, rng=rng)
    preference_model = preference_comparisons.PreferenceModel(reward_net)
    reward_trainer = preference_comparisons.BasicRewardTrainer(
        preference_model=preference_model,
        loss=preference_comparisons.CrossEntropyRewardLoss(),
        epochs=10,
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
        clip_range=0.1,
        ent_coef=0.01,
        gae_lambda=0.95,
        n_epochs=10,
        gamma=0.97,
        learning_rate=2e-3,
        seed=0,
    )

    trajectory_generator = preference_comparisons.AgentTrainer(
        algorithm=agent,
        reward_fn=reward_net,
        venv=venv,
        exploration_frac=0.05,
        rng=rng,
    )

    gatherer = PrefqGatherer(video_dir=video_dir, server_url=SERVER_URL)
    querent = preference_comparisons.PreferenceQuerent()

    pref_comparisons = preference_comparisons.PreferenceComparisons(
        trajectory_generator,
        reward_net,
        num_iterations=60,
        fragmenter=fragmenter,
        preference_gatherer=gatherer,
        reward_trainer=reward_trainer,
        initial_epoch_multiplier=1,
    )

    pref_comparisons.train(total_timesteps=5_000, total_comparisons=200)

    reward, _ = evaluate_policy(agent.policy, venv, 10)
    print("Reward:", reward)
