"""
Tests for the baseline model
"""

import numpy as np
import torch

from heareval.baseline import (
    load_model,
    get_audio_embedding,
    input_sample_rate,
    frame_audio,
)

torch.backends.cudnn.deterministic = True


class TestEmbeddingsTimestamps:
    def setup(self):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = load_model("", device=self.device)
        self.audio = torch.rand(64, 96000, device=self.device) * 2 - 1
        self.embeddings_ct, self.ts_ct = get_audio_embedding(
            audio=self.audio,
            model=self.model,
            frame_rate=input_sample_rate() / 256,
            batch_size=512,
        )

    def teardown(self):
        del self.model
        del self.audio
        del self.embeddings_ct
        del self.ts_ct

    def test_embeddings_replicability(self):
        # Test if all the embeddings are replicable
        embeddings_ct, _ = get_audio_embedding(
            audio=self.audio,
            model=self.model,
            frame_rate=input_sample_rate() / 256,
            batch_size=512,
        )
        for embeddinga, embeddingb in zip(
            self.embeddings_ct.values(), embeddings_ct.values()
        ):
            assert torch.all(torch.abs(embeddinga - embeddingb) < 1e-5)

    def test_embeddings_batched(self):
        # methodA - Pass two audios individually and get embeddings. methodB -
        # Pass the two audio in a batch and get the embeddings. All
        # corresponding embeddings by method A and method B should be similar.
        audioa = self.audio[0].unsqueeze(0)
        audiob = self.audio[1].unsqueeze(0)
        audioab = self.audio[:2]
        assert torch.all(torch.cat([audioa, audiob]) == audioab)

        embeddingsa, _ = get_audio_embedding(
            audio=audioa,
            model=self.model,
            frame_rate=input_sample_rate() / 256,
            batch_size=512,
        )
        embeddingsb, _ = get_audio_embedding(
            audio=audiob,
            model=self.model,
            frame_rate=input_sample_rate() / 256,
            batch_size=512,
        )
        embeddingsab, _ = get_audio_embedding(
            audio=audioab,
            model=self.model,
            frame_rate=input_sample_rate() / 256,
            batch_size=512,
        )

        for embeddinga, embeddingb, embeddingab in zip(
            embeddingsa.values(), embeddingsb.values(), embeddingsab.values()
        ):
            assert torch.allclose(torch.cat([embeddinga, embeddingb]), embeddingab)

    def test_embeddings_sliced(self):
        # Slice the audio to select every even audio in the batch. Produce the
        # embedding for this sliced audio batch. The embeddings for
        # corresponding audios should match the embeddings when the full batch
        # was passed.
        audio_sliced = self.audio[::2]

        # Ensure framing is identical [.???] -> Yes ensuring that.
        audio_sliced_framed, _ = frame_audio(
            audio_sliced,
            frame_size=4096,
            frame_rate=input_sample_rate() / 256,
            sample_rate=input_sample_rate(),
        )
        audio_framed, _ = frame_audio(
            self.audio,
            frame_size=4096,
            frame_rate=input_sample_rate() / 256,
            sample_rate=input_sample_rate(),
        )
        assert torch.all(audio_sliced_framed == audio_framed[::2])

        # Test for centered
        embeddings_sliced, _ = get_audio_embedding(
            audio=audio_sliced,
            model=self.model,
            frame_rate=input_sample_rate() / 256,
            batch_size=512,
        )
        for embedding_sliced, embedding_ct in zip(
            embeddings_sliced.values(), self.embeddings_ct.values()
        ):
            assert torch.allclose(embedding_sliced, embedding_ct[::2])

    def test_embeddings_shape(self):
        # Test the embeddings shape.
        # The shape returned is (batch_size, num_frames, embedding_size). We expect
        # num_frames to be equal to the number of full audio frames that can fit into
        # the audio sample. The centered example is padded with frame_size (4096) number
        # of samples, so we don't need to subtract that in that test.
        for size, embedding in self.embeddings_ct.items():
            assert embedding.shape == (64, 96000 // 256 + 1, int(size))

    def test_embeddings_nan(self):
        # Test for null values in the embeddings.
        for embeddings in [self.embeddings_ct]:
            for size, embedding in embeddings.items():
                assert not torch.any(torch.isnan(embedding))

    def test_embeddings_type(self):
        # Test the data type of the embeddings.
        for embeddings in [self.embeddings_ct]:
            for size, embedding in embeddings.items():
                if size != 20:
                    assert embedding.dtype == torch.float32
                else:
                    assert embedding.dtype == torch.int8

    def test_timestamps_begin(self):
        # Test the beginning of the time stamp
        assert self.ts_ct[0] == 0

    def test_timestamps_spacing(self):
        # Test the spacing between the time stamp
        assert torch.all(torch.abs(torch.diff(self.ts_ct) - self.ts_ct[1]) < 1e-5)

    def test_timestamps_end(self):
        # Test the end of the timestamp.
        duration = self.audio.shape[1] / input_sample_rate()

        # For a centered frame the difference between the end and the duration should
        # be zero (an equal number of frames fit into the padded signal, so the center
        # of the last frame should be right at the end of the input). This is just for
        # this particular input signal.
        centered_diff = duration - self.ts_ct[-1]
        assert np.isclose(centered_diff.detach().cpu().numpy(), 0.0)


class TestModel:
    def setup(self):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = load_model("", device=device)
        self.frames = torch.rand(512, self.model.n_fft, device=device) * 2 - 1

    def teardown(self):
        del self.model
        del self.frames

    def test_model_sliced(self):
        frames_sliced = self.frames[::2]
        assert torch.allclose(frames_sliced[0], self.frames[0])
        assert torch.allclose(frames_sliced[1], self.frames[2])
        assert torch.allclose(frames_sliced, self.frames[::2])

        outputs = self.model(self.frames)
        outputs_sliced = self.model(frames_sliced)

        for output, output_sliced in zip(outputs.values(), outputs_sliced.values()):
            assert torch.allclose(output_sliced[0], output[0])
            assert torch.allclose(output_sliced[1], output[2])
            assert torch.allclose(output_sliced, output[::2])


# class TestLayerbyLayer:
#     def test_layers_find_error(self):

#         device = "cuda:0" if torch.cuda.is_available() else "cpu"
#         model = load_model("", device=device)

#         frames = torch.rand(512, model.n_fft, device=device)
#         frames_sliced = frames[::2, ...]
#         assert torch.all(torch.abs(frames[2] - frames_sliced[1]) == 0)

#         # Layer by the layer perform the same operation on the sliced and the whole frame.
#         # The current error cap is set by changing layer by layer and setting the max possible error.
#         # The purpose is to understand why the batched tests are failing.
#         x = torch.fft.rfft(frames * model.window)
#         y = torch.fft.rfft(frames_sliced * model.window)
#         assert torch.all(torch.abs(x[::2, ...] - y) < 1e-25)

#         x = torch.abs(x) ** 2.0
#         y = torch.abs(y) ** 2.0
#         assert torch.all(torch.abs(x[::2, ...] - y) < 1e-25)

#         # The matmul here is the first point where the error increases to 1e-5
#         x = torch.matmul(x, model.mel_scale.transpose(0, 1))
#         y = torch.matmul(y, model.mel_scale.transpose(0, 1))
#         assert torch.all(torch.abs(x[::2, ...] - y) < 1e-5)

#         x = torch.log(x + model.epsilon)
#         y = torch.log(y + model.epsilon)
#         assert torch.all(torch.abs(x[::2, ...] - y) < 1e-6)

#         # Subsequent increase in error is at the matmuls for the different
#         # embeddings shape.
#         x4096 = x.matmul(model.emb4096)
#         y4096 = y.matmul(model.emb4096)
#         assert torch.all(torch.abs(x4096[::2, ...] - y4096) < 1e-5)

#         x2048 = x.matmul(model.emb2048)
#         y2048 = y.matmul(model.emb2048)
#         assert torch.all(torch.abs(x2048[::2, ...] - y2048) < 1e-4)

#         x512 = x.matmul(model.emb512)
#         y512 = y.matmul(model.emb512)
#         assert torch.all(torch.abs(x512[::2, ...] - y512) < 1e-4)

#         x128 = x.matmul(model.emb128)
#         y128 = y.matmul(model.emb128)
#         assert torch.all(torch.abs(x128[::2, ...] - y128) < 1e-5)

#         int8_max = torch.iinfo(torch.int8).max
#         int8_min = torch.iinfo(torch.int8).min

#         x20 = x.matmul(model.emb20)
#         x20 = model.activation(x20)
#         x20 = x20 * (int8_max - int8_min) + int8_min
#         x20 = x20.type(torch.int8)

#         y20 = y.matmul(model.emb20)
#         y20 = model.activation(y20)
#         y20 = y20 * (int8_max - int8_min) + int8_min
#         y20 = y20.type(torch.int8)
#         assert torch.all(torch.abs(x20[::2, ...] - y20) < 1e-5)


class TestFraming:
    def test_frame_audio(self):

        device = "cuda" if torch.cuda.is_available() else "cpu"

        sr = 44100
        num_audio = 16
        duration = 1.1
        frame_rate = 4.0
        frame_size = 4096

        audio = torch.rand((num_audio, int(sr * duration)), device=device)
        frames, timestamps = frame_audio(
            audio, frame_size=frame_size, frame_rate=frame_rate, sample_rate=sr
        )

        expected_frames_shape = (num_audio, 5, frame_size)
        expected_timestamps = np.arange(0.0, duration, 0.25)

        assert expected_frames_shape == frames.shape
        assert np.all(expected_timestamps == timestamps.detach().cpu().numpy())
