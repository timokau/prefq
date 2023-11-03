"""Adjust imitation modules required for PrefQ to the new gymnasium API."""

# These functions are taken from [1][2] for integration into the new gymnasium API.
# [1] https://imitation.readthedocs.io/en/latest/_modules/imitation/util/util.html
# [2] https://github.com/HumanCompatibleAI/imitation/pull/716/commits/63e9112faf92d195b4b80169d213c3ad17c49c2e

# Disable formatting and linters so we can keep the example as close to the original as possible for now.
# fmt: off
# pylint: skip-file

import os
import shutil
import tempfile
import uuid

import cv2
import gymnasium
import numpy as np

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
        obs, reward, terminated, truncated, info = self.env.step(action)

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

        # NOTE: The following lines are commented out, as they are 
        #       not compatible with the new gymnasium API but appear
        #       in the original class definition.

        # Do not show window of classic control envs
        # if self.env.viewer is not None and self.env.viewer.window.visible:
        #     self.env.viewer.window.set_visible(False)

        return obs, reward, terminated, truncated, info

    def close(self) -> None:
        if self.use_file_cache:
            shutil.rmtree(self.file_cache)
        return super().close()
