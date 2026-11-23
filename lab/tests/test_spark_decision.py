from contextlib import nullcontext
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from lab.spark_decision import load_qwen, make_generator


class Tokens:
    def __init__(self, values):
        self.values = values
        self.shape = ((len(values), len(values[0])) if isinstance(values[0], list) else (len(values),))

    def __getitem__(self, key):
        if isinstance(key, tuple):
            row, columns = key
            return Tokens(self.values[row][columns])
        return Tokens(self.values[key])

    def tolist(self):
        return self.values


class Encoding(dict):
    def __init__(self, rows):
        self.input_ids = Tokens(rows)
        super().__init__(input_ids=self.input_ids)
        self.device = None

    def to(self, device):
        self.device = device
        return self


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.encoded = Encoding([[10, 20, 30]])
        self.tokenizer = Mock(return_value=self.encoded)
        self.tokenizer.decode.return_value = '"blue"'
        self.model = Mock()
        self.model.generate.return_value = Tokens([[10, 20, 30, 40, 50]])
        self.sync = Mock()
        self.generate = make_generator(self.tokenizer, self.model, device="cpu", inference_mode=nullcontext,
                                       synchronize=self.sync)

    def test_meter_and_decode_only_the_completion(self):
        with patch("lab.spark_decision.monotonic_ns", side_effect=(10, 20)):
            result = self.generate("rendered prompt", max_input_tokens=3, max_output_tokens=2)
        self.tokenizer.assert_called_once_with("rendered prompt", return_tensors="pt", truncation=False)
        self.tokenizer.decode.assert_called_once_with([40, 50], skip_special_tokens=True,
                                                      clean_up_tokenization_spaces=False)
        self.assertEqual((result.text, result.input_tokens, result.output_tokens, result.generation_ns),
                         ('"blue"', 3, 2, 10))
        self.assertTrue(result.reached_output_limit)
        self.assertEqual(self.encoded.device, "cpu")
        self.assertEqual(self.sync.call_count, 2)
        self.model.generate.assert_called_once_with(input_ids=self.encoded.input_ids, do_sample=False, num_beams=1,
                                                   num_return_sequences=1, return_dict_in_generate=False,
                                                   max_new_tokens=2)

    def test_input_limit_refuses_before_model_or_device_transfer(self):
        with self.assertRaisesRegex(ValueError, "encoded prompt"):
            self.generate("rendered prompt", max_input_tokens=2, max_output_tokens=2)
        self.model.generate.assert_not_called()
        self.assertIsNone(self.encoded.device)
        self.sync.assert_not_called()

    def test_output_failures_are_not_decoded_as_decisions(self):
        for values, reason in (([[10, 20, 30]], "output token"), ([[10, 20, 30, 40, 50, 60]], "output token"),
                               ([[5, 20, 30, 40]], "prompt prefix"), ([[10, 20, 30, 40]] * 2, "one generated")):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, reason):
                self.model.generate.return_value = Tokens(values)
                self.generate("rendered prompt", max_input_tokens=3, max_output_tokens=2)
        self.tokenizer.decode.assert_not_called()

    def test_noninteger_or_negative_token_ids_are_refused(self):
        self.encoded.input_ids.values[0][0] = 10.0
        with self.assertRaisesRegex(ValueError, "nonnegative integers"):
            self.generate("rendered prompt", max_input_tokens=3, max_output_tokens=2)
        self.model.generate.assert_not_called()
        self.encoded.input_ids.values[0][0] = 10
        for invalid in (40.0, -1, True):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "nonnegative integers"):
                self.model.generate.return_value = Tokens([[10, 20, 30, invalid]])
                self.generate("rendered prompt", max_input_tokens=3, max_output_tokens=2)
        self.tokenizer.decode.assert_not_called()

    def test_loader_passes_offline_flags_and_pinned_container_settings(self):
        torch = Mock()
        model_class, token_class = Mock(), Mock()
        transformers = SimpleNamespace(AutoModelForImageTextToText=model_class, AutoTokenizer=token_class)
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"torch": torch, "transformers": transformers}):
            self.assertTrue(callable(load_qwen(directory)))
        torch.cuda.set_per_process_memory_fraction.assert_called_once_with(0.2, device=0)
        token_class.from_pretrained.assert_called_once_with(directory, local_files_only=True, trust_remote_code=False)
        model_class.from_pretrained.assert_called_once_with(directory, local_files_only=True, trust_remote_code=False,
                                                            use_safetensors=True, dtype=torch.bfloat16)
        model_class.from_pretrained.return_value.to.assert_called_once_with("cuda:0")
