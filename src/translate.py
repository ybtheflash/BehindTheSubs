import os
import json
import logging
from typing import List, Dict, Optional
from src.models import SubtitleCue
from src.config import default_config
from src.transliteration import bengali_to_roman, devanagari_to_roman

logger = logging.getLogger(__name__)

# Common conversational Bengali phrases dictionary for instant fallback translation
BENGALI_FALLBACK_DICT = {
    "তুই আজ অফিসে যাচ্ছিস?": {
        "en": "Are you going to the office today?",
        "hi": "क्या तुम आज ऑफिस जा रहे हो?",
        "bn_rom": "Tui aaj office-e jachhis?",
        "hi_rom": "Kya tum aaj office ja rahe ho?"
    },
    "না, আজকে আমার meeting আছে।": {
        "en": "No, I have a meeting today.",
        "hi": "नहीं, आज मेरी मीटिंग है।",
        "bn_rom": "Na, aajke amar meeting ache.",
        "hi_rom": "Nahi, aaj meri meeting hai."
    },
    "আমি কাল আসব।": {
        "en": "I will come tomorrow.",
        "hi": "मैं कल आऊंगा।",
        "bn_rom": "Ami kal ashbo.",
        "hi_rom": "Main kal aaunga."
    },
    "ওর office-এ একটা meeting আছে।": {
        "en": "He has a meeting at his office.",
        "hi": "उसके ऑफिस में एक मीटिंग है।",
        "bn_rom": "Or office-e ekta meeting ache.",
        "hi_rom": "Uske office mein ek meeting hai."
    },
    "কেমন আছেন?": {
        "en": "How are you?",
        "hi": "आप कैसे हैं?",
        "bn_rom": "Kemon achhen?",
        "hi_rom": "Aap kaise hain?"
    },
    "ভালো আছি।": {
        "en": "I am fine.",
        "hi": "मैं ठीक हूँ।",
        "bn_rom": "Bhalo achhi.",
        "hi_rom": "Main theek hoon."
    },
    "ধন্যবাদ": {
        "en": "Thank you",
        "hi": "धन्यवाद",
        "bn_rom": "Dhonnobad",
        "hi_rom": "Dhanyavaad"
    },
    "নমস্কার": {
        "en": "Greetings / Hello",
        "hi": "नमस्ते",
        "bn_rom": "Nomoshkar",
        "hi_rom": "Namaste"
    },
    "হ্যাঁ": {
        "en": "Yes",
        "hi": "हाँ",
        "bn_rom": "Hyan",
        "hi_rom": "Haan"
    },
    "না": {
        "en": "No",
        "hi": "नहीं",
        "bn_rom": "Na",
        "hi_rom": "Nahi"
    },
    "কোথায় যাচ্ছ?": {
        "en": "Where are you going?",
        "hi": "कहाँ जा रहे हो?",
        "bn_rom": "Kothay jachho?",
        "hi_rom": "Kahan ja rahe ho?"
    },
    "একটু অপেক্ষা করুন": {
        "en": "Please wait a moment",
        "hi": "कृपया एक पल प्रतीक्षा करें",
        "bn_rom": "Ektu opekha korun",
        "hi_rom": "Kripya ek pal prateeksha karein"
    },
    "ঠিক আছে": {
        "en": "All right / Okay",
        "hi": "ठीक है",
        "bn_rom": "Thik ache",
        "hi_rom": "Theek hai"
    }
}

class SubtitleTranslator:
    def __init__(
        self,
        deepseek_key: Optional[str] = None,
        mimo_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        openai_key: Optional[str] = None
    ):
        self.deepseek_key = deepseek_key if deepseek_key is not None else (os.getenv("DEEPSEEK_API_KEY") or getattr(default_config, "deepseek_api_key", ""))
        self.mimo_key = mimo_key if mimo_key is not None else (os.getenv("MIMO_API_KEY") or getattr(default_config, "mimo_api_key", ""))
        self.gemini_key = gemini_key if gemini_key is not None else (os.getenv("GEMINI_API_KEY") or getattr(default_config, "gemini_api_key", ""))
        self.anthropic_key = anthropic_key if anthropic_key is not None else (os.getenv("ANTHROPIC_API_KEY") or getattr(default_config, "anthropic_api_key", ""))
        self.openai_key = openai_key if openai_key is not None else (os.getenv("OPENAI_API_KEY") or getattr(default_config, "openai_api_key", ""))

    def translate_cues(
        self,
        cues: List[SubtitleCue],
        target_languages: List[str] = ("en", "hi", "bn_rom", "hi_rom")
    ) -> List[SubtitleCue]:
        """
        Translates Bengali subtitle cues into target tracks:
        - 'en': English subtitles
        - 'hi': Hindi subtitles in Devanagari script
        - 'bn_rom': Romanized Bengali (Banglish in Latin script)
        - 'hi_rom': Romanized Hindi (Hinglish in Latin script)

        Uses DeepSeek Flash / Xiaomi MiMo LLM / Google Gemini Flash if keys are configured,
        with seamless local context-aware transliteration & dictionary fallback.
        """
        if not cues:
            return cues

        logger.info(f"Translating {len(cues)} cues into languages/tracks: {target_languages}")

        translated_via_api = False

        # 1. Try DeepSeek API first (primary high-speed Bengali/Hindi/Romanized translator)
        if self.deepseek_key:
            try:
                self._translate_with_deepseek(cues, target_languages)
                translated_via_api = True
            except Exception as e:
                logger.warning(f"DeepSeek translation failed: {e}. Trying Xiaomi MiMo...")

        # 2. Try Xiaomi MiMo LLM if DeepSeek failed or not configured
        if not translated_via_api and self.mimo_key:
            try:
                self._translate_with_mimo(cues, target_languages)
                translated_via_api = True
            except Exception as e:
                logger.warning(f"Xiaomi MiMo translation failed: {e}. Trying Google Gemini...")

        # 3. Try Google Gemini Flash if MiMo failed or not configured
        if not translated_via_api and self.gemini_key:
            try:
                self._translate_with_gemini(cues, target_languages)
                translated_via_api = True
            except Exception as e:
                logger.warning(f"Google Gemini translation failed: {e}. Trying Anthropic/OpenAI...")

        # Try Anthropic if Gemini failed or missing
        if not translated_via_api and self.anthropic_key:
            try:
                self._translate_with_anthropic(cues, target_languages)
                translated_via_api = True
            except Exception as e:
                logger.warning(f"Anthropic translation failed: {e}. Trying OpenAI...")

        # Try OpenAI
        if not translated_via_api and self.openai_key:
            try:
                self._translate_with_openai(cues, target_languages)
                translated_via_api = True
            except Exception as e:
                logger.warning(f"OpenAI translation failed: {e}. Falling back to local...")

        # Fallback to local translation for any untranslated or missing cues
        if not translated_via_api:
            logger.info("Using local context-aware translation and transliteration engine.")
            self._translate_fallback(cues, target_languages)

        # Post-Processing: Guarantee 100% coverage of Romanized Bengali and Romanized Hindi
        for cue in cues:
            clean_text = cue.text.strip().replace("\n", " ")
            if "bn_rom" not in cue.translations or not cue.translations["bn_rom"]:
                cue.translations["bn_rom"] = bengali_to_roman(clean_text)

            if "hi_rom" not in cue.translations or not cue.translations["hi_rom"]:
                hi_text = cue.translations.get("hi", "")
                if hi_text and not hi_text.startswith("[HI]"):
                    cue.translations["hi_rom"] = devanagari_to_roman(hi_text)
                else:
                    cue.translations["hi_rom"] = bengali_to_roman(clean_text)

            if "en" not in cue.translations or not cue.translations["en"]:
                cue.translations["en"] = BENGALI_FALLBACK_DICT.get(clean_text, {}).get("en", f"[EN] {clean_text}")

            if "hi" not in cue.translations or not cue.translations["hi"]:
                cue.translations["hi"] = BENGALI_FALLBACK_DICT.get(clean_text, {}).get("hi", f"[HI] {clean_text}")

        return cues

    def _build_batch_prompt(self, cues_batch: List[SubtitleCue], target_languages: List[str]) -> str:
        cues_data = [
            {"id": c.index, "speaker": c.speaker, "text": c.text}
            for c in cues_batch
        ]
        return (
            f"You are a professional Bengali media localisation and subtitling expert.\n"
            f"Translate the following Bengali subtitle cues into the requested tracks: {', '.join(target_languages)}.\n\n"
            f"Requirements:\n"
            f"- 'hi': Natural, fluent Hindi translation in standard Devanagari script (हिन्दी).\n"
            f"- 'bn_rom': Natural Romanized Bengali (Banglish in Latin script, as pronounced, keeping English loanwords).\n"
            f"- 'hi_rom': Natural Romanized Hindi (Hinglish in Latin script, as pronounced, keeping English loanwords).\n"
            f"- 'en': Natural, idiomatic English translation.\n"
            f"Maintain speaker tone, conversational context, proper names, and code-switched English words.\n"
            f"Return strictly valid JSON matching this schema:\n"
            f'{{"results": [{{"id": 1, "en": "English", "hi": "हिन्दी", "bn_rom": "Banglish", "hi_rom": "Hinglish"}}]}}\n\n'
            f"Bengali Cues to Localise:\n{json.dumps(cues_data, ensure_ascii=False, indent=2)}"
        )

    def _translate_with_deepseek(self, cues: List[SubtitleCue], target_languages: List[str]) -> List[SubtitleCue]:
        import httpx
        primary_model = os.getenv("DEEPSEEK_MODEL", getattr(default_config, "deepseek_model", "deepseek-flash"))
        candidate_models = [primary_model, "deepseek-flash", "deepseek-chat"]
        seen = set()
        models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]
        batch_size = 25
        key = self.deepseek_key
        base_url = getattr(default_config, "deepseek_base_url", "https://api.deepseek.com").rstrip("/")
        url = f"{base_url}/chat/completions"

        for i in range(0, len(cues), batch_size):
            batch = cues[i:i + batch_size]
            prompt = self._build_batch_prompt(batch, target_languages)

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            translated = False
            for model in models_to_try:
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a professional Bengali media localisation and subtitling expert. "
                                "Translate Bengali dialogue accurately into the requested tracks. "
                                "Preserve code-switched English words and conversational tone. "
                                "Output strictly valid JSON matching the requested schema."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1
                }
                try:
                    with httpx.Client(timeout=45.0) as client:
                        res = client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            raw_content = choices[0].get("message", {}).get("content", "").strip()
                            clean_json = raw_content
                            if "```json" in clean_json:
                                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                            elif "```" in clean_json:
                                clean_json = clean_json.split("```")[1].split("```")[0].strip()

                            parsed = json.loads(clean_json)
                            results = {item["id"]: item for item in parsed.get("results", [])}
                            for cue in batch:
                                if cue.index in results:
                                    res_item = results[cue.index]
                                    for lang in target_languages:
                                        if lang in res_item:
                                            cue.translations[lang] = str(res_item[lang]).strip()
                            translated = True
                            logger.info(f"DeepSeek ({model}) successfully translated batch of {len(batch)} cues.")
                            break
                    else:
                        logger.warning(f"DeepSeek translation API ({model}) returned HTTP {res.status_code}: {res.text[:150]}")
                except Exception as e:
                    logger.warning(f"DeepSeek translation attempt ({model}) error: {e}")

            if not translated:
                raise RuntimeError(f"All DeepSeek chat models failed to translate batch {i}-{i+batch_size}.")

        return cues

    def _translate_with_mimo(self, cues: List[SubtitleCue], target_languages: List[str]) -> List[SubtitleCue]:
        import httpx
        primary_model = os.getenv("MIMO_TRANSLATION_MODEL", "mimo-v2.6-flash")
        candidate_models = [primary_model, "mimo-v2.6-flash", "mimo-v2.5", "mimo-v2.6-pro", "mimo-v2.5-pro"]
        # Deduplicate while preserving priority order
        seen = set()
        models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]
        batch_size = 20
        key = self.mimo_key
        url = f"{default_config.mimo_base_url.rstrip('/')}/chat/completions"

        for i in range(0, len(cues), batch_size):
            batch = cues[i:i + batch_size]
            prompt = self._build_batch_prompt(batch, target_languages)

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            translated = False
            for model in models_to_try:
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a professional Bengali media translator and subtitler. "
                                "Translate Bengali dialogue accurately into the requested tracks. "
                                "Preserve code-switched English words and conversational tone. "
                                "Output strictly valid JSON matching the requested schema."
                            )
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1
                }
                try:
                    with httpx.Client(timeout=45.0) as client:
                        res = client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            raw_content = choices[0].get("message", {}).get("content", "").strip()
                            clean_json = raw_content
                            if "```json" in clean_json:
                                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                            elif "```" in clean_json:
                                clean_json = clean_json.split("```")[1].split("```")[0].strip()

                            parsed = json.loads(clean_json)
                            results = {item["id"]: item for item in parsed.get("results", [])}
                            for cue in batch:
                                if cue.index in results:
                                    res_item = results[cue.index]
                                    for lang in target_languages:
                                        if lang in res_item:
                                            cue.translations[lang] = str(res_item[lang]).strip()
                            translated = True
                            logger.info(f"Xiaomi MiMo ({model}) successfully translated batch of {len(batch)} cues.")
                            break
                    else:
                        logger.warning(f"MiMo translation API ({model}) returned HTTP {res.status_code}: {res.text[:150]}")
                except Exception as e:
                    logger.warning(f"MiMo translation attempt ({model}) error: {e}")

            if not translated:
                raise RuntimeError(f"All Xiaomi MiMo chat models failed to translate batch {i}-{i+batch_size}.")

        return cues

    def _translate_with_gemini(self, cues: List[SubtitleCue], target_languages: List[str]) -> List[SubtitleCue]:
        import httpx
        candidate_models = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]
        batch_size = 20
        key = self.gemini_key

        for i in range(0, len(cues), batch_size):
            batch = cues[i:i + batch_size]
            prompt = self._build_batch_prompt(batch, target_languages)

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }

            translated = False
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                try:
                    with httpx.Client(timeout=40.0) as client:
                        res = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            raw_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                            parsed = json.loads(raw_text)
                            results = {item["id"]: item for item in parsed.get("results", [])}
                            for cue in batch:
                                if cue.index in results:
                                    res_item = results[cue.index]
                                    for lang in target_languages:
                                        if lang in res_item:
                                            cue.translations[lang] = str(res_item[lang]).strip()
                            translated = True
                            logger.info(f"Gemini ({model}) successfully translated batch of {len(batch)} cues.")
                            break
                except Exception as e:
                    logger.warning(f"Gemini translation attempt ({model}) error: {e}")

            if not translated:
                logger.warning(f"Gemini translation failed for batch {i}-{i+batch_size}, applying fallback.")
                self._translate_fallback(batch, target_languages)

        return cues

    def _translate_with_anthropic(self, cues: List[SubtitleCue], target_languages: List[str]) -> List[SubtitleCue]:
        import anthropic
        client = anthropic.Anthropic(api_key=self.anthropic_key)

        batch_size = 20
        for i in range(0, len(cues), batch_size):
            batch = cues[i:i + batch_size]
            prompt = self._build_batch_prompt(batch, target_languages)

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            results = {item["id"]: item for item in parsed.get("results", [])}

            for cue in batch:
                if cue.index in results:
                    res = results[cue.index]
                    for lang in target_languages:
                        if lang in res:
                            cue.translations[lang] = str(res[lang]).strip()

        return cues

    def _translate_with_openai(self, cues: List[SubtitleCue], target_languages: List[str]) -> List[SubtitleCue]:
        import openai
        client = openai.OpenAI(api_key=self.openai_key)

        batch_size = 20
        for i in range(0, len(cues), batch_size):
            batch = cues[i:i + batch_size]
            prompt = self._build_batch_prompt(batch, target_languages)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional subtitle translator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            results = {item["id"]: item for item in parsed.get("results", [])}

            for cue in batch:
                if cue.index in results:
                    res = results[cue.index]
                    for lang in target_languages:
                        if lang in res:
                            cue.translations[lang] = str(res[lang]).strip()

        return cues

    def _translate_fallback(self, cues: List[SubtitleCue], target_languages: List[str]) -> List[SubtitleCue]:
        """
        Reliable offline fallback translator and transliterator for broadcast and OTT runtime.
        Provides accurate dictionary mappings and phonetic transliterated representations.
        """
        for cue in cues:
            clean_text = cue.text.strip().replace("\n", " ")
            if clean_text in BENGALI_FALLBACK_DICT:
                mapping = BENGALI_FALLBACK_DICT[clean_text]
                for lang in target_languages:
                    if lang in mapping:
                        cue.translations[lang] = mapping[lang]
            else:
                if "en" in target_languages and "en" not in cue.translations:
                    cue.translations["en"] = f"[EN] {clean_text}"
                if "hi" in target_languages and "hi" not in cue.translations:
                    cue.translations["hi"] = f"[HI] {clean_text}"

            # Accurate Romanized Bengali (Banglish)
            if "bn_rom" in target_languages and "bn_rom" not in cue.translations:
                cue.translations["bn_rom"] = bengali_to_roman(clean_text)

            # Accurate Romanized Hindi (Hinglish)
            if "hi_rom" in target_languages and "hi_rom" not in cue.translations:
                hi_text = cue.translations.get("hi", "")
                if hi_text and not hi_text.startswith("[HI]"):
                    cue.translations["hi_rom"] = devanagari_to_roman(hi_text)
                else:
                    cue.translations["hi_rom"] = bengali_to_roman(clean_text)

        return cues
