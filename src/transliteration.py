"""
Rule-Based Phonetic Transliteration Engine for:
1. Bengali Script -> Romanized Bengali (Banglish in Latin alphabet)
2. Devanagari Script -> Romanized Hindi (Hinglish in Latin alphabet)

Provides fast, 100% deterministic, offline transliteration for broadcast & OTT subtitles.
"""

import re

# Bengali to Roman mapping
BN_VOWELS = {
    'অ': 'o', 'আ': 'a', 'ই': 'i', 'ঈ': 'i', 'উ': 'u', 'ঊ': 'u',
    'ঋ': 'ri', 'এ': 'e', 'ঐ': 'oi', 'ও': 'o', 'ঔ': 'ou'
}

BN_MATRAS = {
    'া': 'a', 'ি': 'i', 'ী': 'i', 'ু': 'u', 'ূ': 'u',
    'ৃ': 'ri', 'ে': 'e', 'ৈ': 'oi', 'ো': 'o', 'ৌ': 'ou',
    '্': ''  # Hasanta / virama
}

BN_CONSONANTS = {
    'ক': 'k', 'খ': 'kh', 'গ': 'g', 'ঘ': 'gh', 'ঙ': 'ng',
    'চ': 'ch', 'ছ': 'chh', 'জ': 'j', 'ঝ': 'jh', 'ঞ': 'n',
    'ট': 't', 'ঠ': 'th', 'ড': 'd', 'ঢ': 'dh', 'ণ': 'n',
    'ত': 't', 'থ': 'th', 'দ': 'd', 'ধ': 'dh', 'ন': 'n',
    'প': 'p', 'ফ': 'ph', 'ব': 'b', 'ভ': 'bh', 'ম': 'm',
    'য': 'j', 'র': 'r', 'ল': 'l', 'শ': 'sh', 'ষ': 'sh',
    'স': 's', 'হ': 'h', 'ড়': 'r', 'ঢ়': 'rh', 'য়': 'y',
    'ৎ': 't', 'ং': 'ng', 'ঃ': 'h', 'ঁ': 'n'
}

# Devanagari to Roman mapping
HI_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऑ': 'o'
}

HI_MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o',
    '्': ''  # Halant
}

HI_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
    'ष': 'sh', 'स': 's', 'ह': 'h', 'ड़': 'r', 'ढ़': 'rh',
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'फ़': 'f',
    'ं': 'n', 'ः': 'h', 'ँ': 'n'
}

def bengali_to_roman(text: str) -> str:
    """
    Converts Bengali text into natural Romanized Bengali (Banglish).
    Preserves English words, numbers, and punctuation.
    """
    if not text:
        return ""

    out = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        # Consonant
        if char in BN_CONSONANTS:
            base = BN_CONSONANTS[char]
            # Check next character
            if i + 1 < n:
                next_c = text[i + 1]
                if next_c == '্':  # virama / conjunct
                    out.append(base)
                    i += 2
                    continue
                elif next_c in BN_MATRAS:  # vowel sign
                    out.append(base + BN_MATRAS[next_c])
                    i += 2
                    continue
                elif next_c in BN_CONSONANTS:  # inherent vowel 'o' or 'a'
                    out.append(base + 'o')
                    i += 1
                    continue
                else:
                    out.append(base)
                    i += 1
                    continue
            else:
                out.append(base)
                i += 1
                continue

        # Independent Vowel
        elif char in BN_VOWELS:
            out.append(BN_VOWELS[char])
            i += 1

        # Matra standalone
        elif char in BN_MATRAS:
            out.append(BN_MATRAS[char])
            i += 1

        # Bengali Punctuation Dari '।'
        elif char == '।':
            out.append('.')
            i += 1

        # Pass through numbers, spaces, English characters, and standard punctuation
        else:
            out.append(char)
            i += 1

    result = ''.join(out)
    # Clean up double vowels or awkward spacing
    result = re.sub(r' +', ' ', result).strip()
    return result

def devanagari_to_roman(text: str) -> str:
    """
    Converts Hindi Devanagari text into natural Romanized Hindi (Hinglish).
    Preserves English words, numbers, and punctuation.
    """
    if not text:
        return ""

    out = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        # Consonant
        if char in HI_CONSONANTS:
            base = HI_CONSONANTS[char]
            if i + 1 < n:
                next_c = text[i + 1]
                if next_c == '्':  # halant
                    out.append(base)
                    i += 2
                    continue
                elif next_c in HI_MATRAS:
                    out.append(base + HI_MATRAS[next_c])
                    i += 2
                    continue
                elif next_c in HI_CONSONANTS:
                    out.append(base + 'a')
                    i += 1
                    continue
                else:
                    out.append(base)
                    i += 1
                    continue
            else:
                out.append(base)
                i += 1
                continue

        # Independent vowel
        elif char in HI_VOWELS:
            out.append(HI_VOWELS[char])
            i += 1

        # Matra
        elif char in HI_MATRAS:
            out.append(HI_MATRAS[char])
            i += 1

        # Punctuation Purna Viram '।'
        elif char == '।':
            out.append('.')
            i += 1

        else:
            out.append(char)
            i += 1

    result = ''.join(out)
    result = re.sub(r' +', ' ', result).strip()
    return result
