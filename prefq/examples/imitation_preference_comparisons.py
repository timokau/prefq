# This example is taken from [1] (MIT licensed). It does not currently use PrefQ.
# It only serves to show that the `imitation` dependency is working.
# [1] https://github.com/HumanCompatibleAI/imitation/blob/19c7f35d7cac97e623f352d367fa384f5f3bb465/docs/algorithms/preference_comparisons.rst

# Disable formatting and linters so we can keep the example as close to the original as possible for now.
# fmt: off
# pylint: skip-file

import json
import os
import pathlib
import tempfile
import time

# Despite receiving this warning, videos are still rendered correctly. The warning can therefore safely be ignored
import warnings
from typing import Optional, Sequence, Tuple

import numpy as np
import requests
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

warnings.filterwarnings("ignore", message="OpenCV: FFMPEG: tag 0x30395056/'VP90' is not supported with codec id 167 and format 'webm / WebM'")

SERVER_URL = "http://127.0.0.1:5000/"

# This class is a slightly modified version of the PrefCollectGatherer introduced in https://github.com/HumanCompatibleAI/imitation/pull/716
class PrefqGatherer(SynchronousHumanGatherer):
    """Gatherer for synchronous communication with a flask webserver."""

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

    def __call__(self) -> Tuple[Sequence[TrajectoryWithRewPair], np.ndarray]:
        """Iteratively sends video-pairs associated with a Query-ID to server."""

        n_pending_queries = len(self.pending_queries)
        preferences = np.zeros(n_pending_queries, dtype=np.float32)
        requests.post(self.server_url + "videos", json={"n_pending_queries": n_pending_queries})

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

            self._send_videos_to_server(query_id)

        
        feedback_data = self._get_feedback_from_server()

        for query_id, is_left_preferred in feedback_data.items():
            print(f"    Query ID: {query_id}    Left Video Preferred: {is_left_preferred}")
            preferences = np.zeros(len(self.pending_queries), dtype=np.float32)
            preferences[i] = 1 if is_left_preferred else 0

        queries = list(self.pending_queries.values())
        self.pending_queries.clear()

        return queries, preferences


    def _send_videos_to_server(self, query_id):
        print("\nPrefqGatherer: sending videos to server...")

        left_filename = f"{query_id}-left.webm"
        right_filename = f"{query_id}-right.webm"

        left_filepath = os.path.join(self.video_dir, left_filename)
        right_filepath = os.path.join(self.video_dir, right_filename)

        with open(left_filepath, "rb") as left_file, open(
            right_filepath, "rb"
        ) as right_file:
            # Read the file data into memory
            left_video_data = left_file.read()
            right_video_data = right_file.read()

        payload = {
            "left_video": (
                left_filename,
                left_video_data,
                "application/octet-stream",
            ),
            "right_video": (
                right_filename,
                right_video_data,
                "application/octet-stream",
            ),
            "query_id": (
                json.dumps(query_id),
                "application/json",
            ),
        }

        response = requests.post(self.server_url + "videos", files=payload, timeout=10)

        if response.status_code >= 200 % response.status_code < 400:
            print("PrefqGatherer: Payload transferred")
        else:
            print("PrefqGatherer: Error while sending videos")
            print(response.status_code)

        print("PrefqGatherer: ...videos sent to server\n")


    def _get_feedback_from_server(self):
        """
        GET-Request: Receive client feedback from Server
        
            After rendering all videos, the PrefQGatherer enters
            a blocking while loop, until the server has received
            all feedback data from the Feedback Client.
        """

        print("\n\PrefqGatherer: Starting request_feedback() [...]")
        
        def _wait_for_feedback_request(url):
            while True:
                time.sleep(5)
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    feedback_data = response.json()
                    if feedback_data == {}:
                        print("Query Client: Waiting for feedback...")
                        continue
                    else: 
                        print("Query Client: Feedback received")
                        break
            return feedback_data

        feedback_data = _wait_for_feedback_request(self.server_url + "feedback")
        return feedback_data

rng = np.random.default_rng(0)
video_dir = tempfile.mkdtemp(prefix="videos_")

venv = make_vec_env(env_name = "Pendulum-v1", 
                    rng=rng,
                    post_wrappers=[lambda env, env_id: RenderImageInfoWrapper(env, use_file_cache=True)],
)

reward_net = BasicRewardNet(
    venv.observation_space, venv.action_space, normalize_input_layer=RunningNorm,
)

fragmenter = preference_comparisons.RandomFragmenter(warning_threshold=0, rng=rng)
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
    seed=0,
)

trajectory_generator = preference_comparisons.AgentTrainer(
    algorithm=agent,
    reward_fn=reward_net,
    venv=venv,
    exploration_frac=0.0,
    rng=rng,
)

gatherer = PrefqGatherer(video_dir = video_dir, server_url=SERVER_URL)
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
