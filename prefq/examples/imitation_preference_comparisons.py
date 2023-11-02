# This example is taken from [1] (MIT licensed). It does not currently use PrefQ.
# It only serves to show that the `imitation` dependency is working.
# [1] https://github.com/HumanCompatibleAI/imitation/blob/19c7f35d7cac97e623f352d367fa384f5f3bb465/docs/algorithms/preference_comparisons.rst

# Disable formatting and linters so we can keep the example as close to the original as possible for now.
# fmt: off
# pylint: skip-file

import functools
import json
import os
import pathlib
import shutil
import tempfile
import time
import uuid

# Despite receiving this warning, videos are still rendered correctly. The warning can therefore safely be ignored
import warnings
from typing import (
    Any,
    Callable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)

import cv2
import gymnasium
import numpy as np
import requests
from imitation.algorithms import preference_comparisons
from imitation.algorithms.preference_comparisons import (
    SynchronousHumanGatherer,
    write_fragment_video,
)
from imitation.data.types import TrajectoryWithRewPair
from imitation.policies.base import FeedForward32Policy, NormalizeFeaturesExtractor
from imitation.rewards.reward_nets import BasicRewardNet
from imitation.util import logger as imit_logger
from imitation.util.networks import RunningNorm
from imitation.util.util import make_vec_env
from stable_baselines3 import PPO
from stable_baselines3.common import monitor
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv

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


# Adjust RenderImageInfoWrapper to new gymnasium API
# https://stackoverflow.com/questions/73195438/openai-gyms-env-step-what-are-the-values   
class RenderImageInfoWrapper(gymnasium.Wrapper):
    """Saves render images to `info`.

    Can be very memory intensive for large render images.
    Use `scale_factor` to reduce render image size.
    If you need to preserve the resolution and memory
    runs out, you can activate `use_file_cache` to save
    rendered images and instead put their path into `info`.
    """

    def __init__(
        self,
        env: gymnasium.Env,
        scale_factor: float = 1.0,
        use_file_cache: bool = False,
    ):
        """Builds RenderImageInfoWrapper.

        Args:
            env: Environment to wrap.
            scale_factor: scales rendered images to be stored.
            use_file_cache: whether to save rendered images to disk.
        """
        super().__init__(env)
        self.scale_factor = scale_factor
        self.use_file_cache = use_file_cache
        if self.use_file_cache:
            self.file_cache = tempfile.mkdtemp("imitation_RenderImageInfoWrapper")

    def step(self, action):

        obs, reward, terminated, trunctaded, info = self.env.step(action)

        rendered_image = self.render()
        # Scale the render image
        scaled_size = (
            int(self.scale_factor * rendered_image.shape[0]),
            int(self.scale_factor * rendered_image.shape[1]),
        )
        scaled_rendered_image = cv2.resize(
            rendered_image,
            scaled_size,
            interpolation=cv2.INTER_AREA,
        )
        # Store the render image
        if not self.use_file_cache:
            info["rendered_img"] = scaled_rendered_image
        else:
            unique_file_path = os.path.join(
                self.file_cache,
                str(uuid.uuid4()) + ".npy",
            )
            np.save(unique_file_path, scaled_rendered_image)
            info["rendered_img"] = unique_file_path

        # IMPORTANT NOTE: The following lines are commented out, as they are not compatible with the new gymnasium API and
        #                 seem to not be necessary for PrefQ. However, eventual side effects should be investigated in future.

        # Do not show window of classic control envs
        # if self.env.viewer is not None and self.env.viewer.window.visible:
        #     self.env.viewer.window.set_visible(False)

        return obs, reward, terminated, trunctaded, info

    def close(self) -> None:
        if self.use_file_cache:
            shutil.rmtree(self.file_cache)
        return super().close()


def make_vec_env(
    env_name: str,
    render_mode: str,
    *,
    rng: np.random.Generator,
    n_envs: int = 8,
    parallel: bool = False,
    log_dir: Optional[str] = None,
    max_episode_steps: Optional[int] = None,
    post_wrappers: Optional[Sequence[Callable[[gymnasium.Env, int], gymnasium.Env]]] = None,
    env_make_kwargs: Optional[Mapping[str, Any]] = None,
) -> VecEnv:
    """Makes a vectorized environment.

    Args:
        env_name: The Env's string id in Gym.
        rng: The random state to use to seed the environment.
        n_envs: The number of duplicate environments.
        parallel: If True, uses SubprocVecEnv; otherwise, DummyVecEnv.
        log_dir: If specified, saves Monitor output to this directory.
        max_episode_steps: If specified, wraps each env in a TimeLimit wrapper
            with this episode length. If not specified and `max_episode_steps`
            exists for this `env_name` in the Gym registry, uses the registry
            `max_episode_steps` for every TimeLimit wrapper (this automatic
            wrapper is the default behavior when calling `gym.make`). Otherwise
            the environments are passed into the VecEnv unwrapped.
        post_wrappers: If specified, iteratively wraps each environment with each
            of the wrappers specified in the sequence. The argument should be a Callable
            accepting two arguments, the Env to be wrapped and the environment index,
            and returning the wrapped Env.
        env_make_kwargs: The kwargs passed to `spec.make`.

    Returns:
        A VecEnv initialized with `n_envs` environments.
    """
    # Resolve the spec outside of the subprocess first, so that it is available to
    # subprocesses running `make_env` via automatic pickling.
    # Just to ensure packages are imported and spec is properly resolved
    tmp_env = gymnasium.make(env_name, render_mode=render_mode)
    tmp_env.close()
    spec = tmp_env.spec
    env_make_kwargs = env_make_kwargs or {}

    def make_env(i: int, this_seed: int) -> gymnasium.Env:
        # Previously, we directly called `gym.make(env_name)`, but running
        # `imitation.scripts.train_adversarial` within `imitation.scripts.parallel`
        # created a weird interaction between Gym and Ray -- `gym.make` would fail
        # inside this function for any of our custom environment unless those
        # environments were also `gym.register()`ed inside `make_env`. Even
        # registering the custom environment in the scope of `make_vec_env` didn't
        # work. For more discussion and hypotheses on this issue see PR #160:
        # https://github.com/HumanCompatibleAI/imitation/pull/160.
        assert env_make_kwargs is not None  # Note: to satisfy mypy
        assert spec is not None  # Note: to satisfy mypy
        env = gymnasium.make(spec, max_episode_steps=max_episode_steps, render_mode=render_mode, **env_make_kwargs)

        # Seed each environment with a different, non-sequential seed for diversity
        # (even if caller is passing us sequentially-assigned base seeds). int() is
        # necessary to work around gym bug where it chokes on numpy int64s.
        env.reset(seed=int(this_seed))
        # NOTE: we do it here rather than on the final VecEnv, because
        # that would set the same seed for all the environments.

        # Use Monitor to record statistics needed for Baselines algorithms logging
        # Optionally, save to disk
        log_path = None
        if log_dir is not None:
            log_subdir = os.path.join(log_dir, "monitor")
            os.makedirs(log_subdir, exist_ok=True)
            log_path = os.path.join(log_subdir, f"mon{i:03d}")

        env = monitor.Monitor(env, log_path)

        if post_wrappers:
            for wrapper in post_wrappers:
                env = wrapper(env, i)

        return env

    env_seeds = make_seeds(rng, n_envs)
    env_fns: List[Callable[[], gymnasium.Env]] = [
        functools.partial(make_env, i, s) for i, s in enumerate(env_seeds)
    ]
    if parallel:
        # See GH hill-a/stable-baselines issue #217
        return SubprocVecEnv(env_fns, start_method="forkserver")
    else:
        return DummyVecEnv(env_fns)
    
@overload
def make_seeds(
    rng: np.random.Generator,
) -> int:
    ...

@overload
def make_seeds(rng: np.random.Generator, n: int) -> List[int]:
    ...

def make_seeds(
    rng: np.random.Generator,
    n: Optional[int] = None,
) -> Union[Sequence[int], int]:
    """Generate n random seeds from a random state.

    Args:
        rng: The random state to use to generate seeds.
        n: The number of seeds to generate.

    Returns:
        A list of n random seeds.
    """
    seeds_arr = rng.integers(0, (1 << 31) - 1, (n if n is not None else 1,))
    seeds: List[int] = seeds_arr.tolist()
    if n is None:
        return seeds[0]
    else:
        return seeds



rng = np.random.default_rng(0)
video_dir = tempfile.mkdtemp(prefix="videos_")

venv = make_vec_env(env_name = "Pendulum-v1", 
                    render_mode="rgb_array",
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
