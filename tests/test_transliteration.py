import pytest
from src.transliteration import bengali_to_roman, devanagari_to_roman

def test_bengali_to_roman_basic():
    # Bengali greeting and phrase
    text = "আমি কাল আসব।"
    roman = bengali_to_roman(text)
    assert "ami" in roman.lower()
    assert "kal" in roman.lower() or "kaal" in roman.lower()

def test_bengali_to_roman_code_switched():
    # Mixed Bengali + English words
    text = "ওর office-এ একটা meeting আছে।"
    roman = bengali_to_roman(text)
    assert "office" in roman.lower()
    assert "meeting" in roman.lower()

def test_devanagari_to_roman_basic():
    # Hindi phrase
    text = "मैं कल आऊंगा।"
    roman = devanagari_to_roman(text)
    assert "kal" in roman.lower() or "aaunga" in roman.lower() or "main" in roman.lower()

def test_devanagari_to_roman_code_switched():
    text = "उसके ऑफिस में एक मीटिंग है।"
    roman = devanagari_to_roman(text)
    assert len(roman) > 0
    # Should contain latin characters
    assert any('a' <= c <= 'z' for c in roman.lower())
