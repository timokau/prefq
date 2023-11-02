"""Adjust imitation modules required for PrefQ to the new gymnasium API."""

# These functions are taken from [1][2] for integration into the new gymnasium API.
# [1] https://imitation.readthedocs.io/en/latest/_modules/imitation/util/util.html
# [2] https://github.com/HumanCompatibleAI/imitation/pull/716/commits/63e9112faf92d195b4b80169d213c3ad17c49c2e

# Disable formatting and linters so we can keep the example as close to the original as possible for now.
# fmt: off
# pylint: skip-file

import functools
import os
import shutil
import tempfile
import uuid
from typing import Any, Callable, List, Mapping, Optional, Sequence, Union, overload

import cv2
import gymnasium
import numpy as np
from stable_baselines3.common import monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv

# This Class has been taken from
# https://github.com/HumanCompatibleAI/imitation/pull/716/commits/63e9112faf92d195b4b80169d213c3ad17c49c2e


# Due to the update of the gymnasium API, several changes had to be made,
# in order to make the code compatible with the new package
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

        # IMPORTANT NOTE: The following lines are commented out, as they are 
        #                 not compatible with the new gymnasium API and seem
        #                 to not be necessary for PrefQ. However, eventual
        #                 side effects should be investigated in future.

        # Do not show window of classic control envs
        # if self.env.viewer is not None and self.env.viewer.window.visible:
        #     self.env.viewer.window.set_visible(False)

        return obs, reward, terminated, trunctaded, info

    def close(self) -> None:
        if self.use_file_cache:
            shutil.rmtree(self.file_cache)
        return super().close()


# This function has been taken from
# https://imitation.readthedocs.io/en/latest/_modules/imitation/util/util.html
# and adjusted to the new gymnasium API
def make_vec_env(
    env_name: str,
    render_mode: str,
    *,
    rng: np.random.Generator,
    n_envs: int = 8,
    parallel: bool = False,
    log_dir: Optional[str] = None,
    max_episode_steps: Optional[int] = None,
    post_wrappers: Optional[
        Sequence[Callable[[gymnasium.Env, int], gymnasium.Env]]
    ] = None,
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
        env = gymnasium.make(
            spec,
            max_episode_steps=max_episode_steps,
            render_mode=render_mode,
            **env_make_kwargs,
        )

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
