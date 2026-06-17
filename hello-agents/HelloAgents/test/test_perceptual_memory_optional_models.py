import builtins
import os
import unittest
from unittest.mock import patch

from mem.types.perceptual import PerceptualMemory


class PerceptualMemoryOptionalModelsTest(unittest.TestCase):
    def test_multimodal_models_are_not_imported_by_default(self):
        memory = PerceptualMemory.__new__(PerceptualMemory)
        memory.vector_dim = 384
        memory._clip_model = None
        memory._clip_processor = None
        memory._clap_model = None
        memory._clap_processor = None
        memory._image_dim = 384
        memory._audio_dim = 384

        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "transformers" or name.startswith("transformers."):
                raise AssertionError("transformers should not be imported unless explicitly enabled")
            return original_import(name, *args, **kwargs)

        with patch.dict(os.environ, {
            "PERCEPTUAL_ENABLE_CLIP": "0",
            "PERCEPTUAL_ENABLE_CLAP": "0",
        }, clear=False):
            with patch("builtins.__import__", side_effect=guarded_import):
                memory._init_optional_multimodal_models()

        self.assertIsNone(memory._clip_model)
        self.assertIsNone(memory._clip_processor)
        self.assertIsNone(memory._clap_model)
        self.assertIsNone(memory._clap_processor)
        self.assertEqual(memory._image_dim, 384)
        self.assertEqual(memory._audio_dim, 384)


if __name__ == "__main__":
    unittest.main()
