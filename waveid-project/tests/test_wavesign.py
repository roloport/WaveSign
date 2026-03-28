"""Tests for WaveSign engine (sign and verify)."""

import numpy as np
import pytest
from PIL import Image

from waveid.wavesign import WaveSignEngine, WaveSignError


@pytest.fixture
def engine():
    return WaveSignEngine(key="test-secret-key")


@pytest.fixture
def test_image():
    """Create a 200x200 test image with varied content."""
    rng = np.random.RandomState(42)
    data = rng.randint(50, 200, (200, 200, 3), dtype=np.uint8)
    return Image.fromarray(data)


@pytest.fixture
def small_payload():
    return b"waveid:test:abv-data-here-32bytes!"


class TestWaveSignEngine:
    def test_sign_produces_image_and_verify_data(self, engine, test_image, small_payload):
        signed_img, verify_data = engine.sign(test_image, small_payload)
        assert signed_img.size == test_image.size
        assert signed_img.mode == "RGB"
        assert len(verify_data) > 0

    def test_signed_image_visually_similar(self, engine, test_image, small_payload):
        """Signed image should have high PSNR (invisible changes)."""
        signed_img, _ = engine.sign(test_image, small_payload)

        orig = np.array(test_image, dtype=np.float64)
        signed = np.array(signed_img, dtype=np.float64)
        mse = np.mean((orig - signed) ** 2)
        if mse > 0:
            psnr = 10 * np.log10(255.0**2 / mse)
            assert psnr > 30  # Should be imperceptible

    def test_verify_valid_signature(self, engine, test_image, small_payload):
        signed_img, verify_data = engine.sign(test_image, small_payload)
        is_valid, extracted = engine.verify(signed_img, verify_data)
        assert is_valid
        assert extracted == small_payload

    def test_verify_detects_pixel_tampering(self, engine, test_image, small_payload):
        signed_img, verify_data = engine.sign(test_image, small_payload)

        # Tamper with the signed image
        arr = np.array(signed_img)
        arr[50, 50] = [255, 0, 0]  # Red pixel
        tampered = Image.fromarray(arr)

        is_valid, _ = engine.verify(tampered, verify_data)
        assert not is_valid

    def test_verify_wrong_key(self, test_image, small_payload):
        engine1 = WaveSignEngine(key="key-1")
        engine2 = WaveSignEngine(key="key-2")

        signed_img, verify_data = engine1.sign(test_image, small_payload)
        is_valid, _ = engine2.verify(signed_img, verify_data)
        assert not is_valid

    def test_verify_corrupted_verify_data(self, engine, test_image, small_payload):
        signed_img, verify_data = engine.sign(test_image, small_payload)

        corrupted = bytearray(verify_data)
        corrupted[10] ^= 0xFF
        is_valid, _ = engine.verify(signed_img, bytes(corrupted))
        assert not is_valid

    def test_payload_too_large(self, engine):
        tiny_image = Image.new("RGB", (10, 10), color=(128, 128, 128))
        huge_payload = b"\x00" * 10000
        with pytest.raises(WaveSignError):
            engine.sign(tiny_image, huge_payload)
