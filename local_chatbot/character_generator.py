import json
import random
import re
from dataclasses import dataclass

from model_harness import ModelConfig
from .client import chat_completion
from .paths import CHARACTER_METADATA_DIR
from .storage import Character, CharacterProfile, create_character, sanitize_name


@dataclass(frozen=True)
class WorldBuildingData:
    races: list[str]
    classes: list[str]
    pronouns: list[str]
    given_names: list[str]
    family_names: list[str]
    origins: list[str]
    motivations: list[str]


class RandomCharacterGenerator:
    """Generate lightweight D&D 5e-inspired character profiles."""

    WORLD_BUILDING_PATH = CHARACTER_METADATA_DIR / "world_building.json"
    WORLD_BUILDING_KEYS = {
        "races": 1,
        "classes": 1,
        "pronouns": 1,
        "given_names": 1,
        "family_names": 1,
        "origins": 1,
        "motivations": 2,
    }

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self.world = self.load_world_building()

    def generate_profiles(self, count: int = 5, model_config: ModelConfig | None = None) -> list[CharacterProfile]:
        used_names: set[str] = set()
        profiles = []
        for _ in range(count):
            profile = self.generate_profile(used_names, model_config)
            profiles.append(profile)
            used_names.add(sanitize_name(profile.name))
        return profiles

    def create_characters(self, count: int = 5, model_config: ModelConfig | None = None) -> list[Character]:
        characters = []
        for profile in self.generate_profiles(count, model_config):
            try:
                characters.append(create_character(profile))
            except FileExistsError:
                unique_profile = self.with_unique_name(profile)
                characters.append(create_character(unique_profile))
        return characters

    def generate_profile(
        self,
        used_names: set[str] | None = None,
        model_config: ModelConfig | None = None,
    ) -> CharacterProfile:
        used_names = used_names or set()
        name = self.unique_name(used_names)
        pronouns = self.random.choice(self.world.pronouns)
        gender = self.gender_from_pronouns(pronouns)
        level = str(self.random.randint(1, 10))
        race = self.random.choice(self.world.races)
        character_class = self.random.choice(self.world.classes)
        origin = self.random.choice(self.world.origins)
        motivations = self.random.sample(self.world.motivations, k=2)
        first_name = self.first_name(name)
        backstory = self.draft_backstory(first_name, level, race, character_class, origin, motivations)
        profile = CharacterProfile(
            name=name,
            pronouns=pronouns,
            level=level,
            race=race,
            character_class=character_class,
            backstory=backstory,
            summary=(
                f"{first_name} is a {gender} {race} {character_class} from {origin}, "
                f"torn between a need to {motivations[0]} and a need to {motivations[1]}."
            ),
            motivations=motivations,
            drives=motivations,
            alliances=[],
            enemies=[],
            origin=origin,
            gender=gender,
        )
        if model_config:
            return self.with_model_backstory(profile, model_config)
        return profile

    def unique_name(self, used_names: set[str]) -> str:
        for _ in range(200):
            name = f"{self.random.choice(self.world.given_names)} {self.random.choice(self.world.family_names)}"
            if sanitize_name(name) not in used_names:
                return name
        return f"{self.random.choice(self.world.given_names)} {self.random.randint(1000, 9999)}"

    def with_unique_name(self, profile: CharacterProfile) -> CharacterProfile:
        suffix = self.random.randint(1000, 9999)
        name = f"{profile.name} {suffix}"
        return CharacterProfile(
            name=name,
            pronouns=profile.pronouns,
            level=profile.level,
            race=profile.race,
            character_class=profile.character_class,
            backstory=profile.backstory.replace(profile.name, name),
            summary=profile.summary.replace(profile.name, name).replace(self.first_name(profile.name), self.first_name(name)),
            motivations=profile.motivations,
            drives=profile.drives,
            alliances=profile.alliances,
            enemies=profile.enemies,
            origin=profile.origin,
            gender=profile.gender,
        )

    def with_model_backstory(self, profile: CharacterProfile, model_config: ModelConfig) -> CharacterProfile:
        first_name = self.first_name(profile.name)
        prompt = (
            "Create a believable tabletop fantasy character profile from these base stats.\n\n"
            f"Full name: {profile.name}\n"
            f"First name to use in prose: {first_name}\n"
            f"Level: {profile.level}\n"
            f"Race: {profile.race}\n"
            f"Class: {profile.character_class}\n"
            f"Pronouns: {profile.pronouns}\n"
            f"Gender: {profile.gender}\n"
            f"Place of origin: {profile.origin}\n\n"
            "Selected character motivations:\n"
            f"1. {profile.motivations[0] if profile.motivations else 'choose a personal goal'}\n"
            f"2. {profile.motivations[1] if profile.motivations and len(profile.motivations) > 1 else 'choose a competing personal goal'}\n\n"
            "Requirements:\n"
            "- Write a detailed backstory with as many paragraphs as needed.\n"
            "- Make the character feel grounded and believable, with concrete relationships, losses, skills, and flaws.\n"
            "- Use both selected motivations and contemplate how they assist each other, compete with each other, or both.\n"
            "- Use the first name only in the backstory and summary. Do not use the family name outside the title metadata.\n"
            "- Write the summary last as 1 or 2 sentences.\n"
            "- Return only this format:\n"
            "BACKSTORY:\n"
            "<three paragraphs>\n\n"
            "SUMMARY:\n"
            "<one or two sentences>\n"
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You write concise, grounded fantasy character biographies. "
                    "You follow formatting instructions exactly."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        response = chat_completion(model_config, messages, temperature=0.9, max_tokens=1100)
        try:
            payload = self.parse_model_markdown(response)
        except ValueError:
            messages.extend(
                [
                    {"role": "assistant", "content": response},
                    {
                        "role": "user",
                        "content": (
                            "Reformat your last answer using only this plain text structure:\n"
                            "BACKSTORY:\n"
                            "<detailed backstory>\n\n"
                            "SUMMARY:\n"
                            "<one or two sentences>"
                        ),
                    },
                ]
            )
            response = chat_completion(model_config, messages, temperature=0.2, max_tokens=1100)
            payload = self.parse_model_markdown(response)
        backstory = self.normalize_backstory(payload.get("backstory", profile.backstory))
        summary = payload.get("summary", profile.summary).strip()
        return CharacterProfile(
            name=profile.name,
            pronouns=profile.pronouns,
            level=profile.level,
            race=profile.race,
            character_class=profile.character_class,
            backstory=backstory,
            summary=summary,
            motivations=profile.motivations,
            drives=profile.drives,
            alliances=profile.alliances,
            enemies=profile.enemies,
            origin=profile.origin,
            gender=profile.gender,
        )

    @classmethod
    def load_world_building(cls) -> WorldBuildingData:
        if not cls.WORLD_BUILDING_PATH.exists():
            raise FileNotFoundError(f"Missing world building data: {cls.WORLD_BUILDING_PATH}")
        payload = json.loads(cls.WORLD_BUILDING_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{cls.WORLD_BUILDING_PATH} must contain a JSON object.")

        data: dict[str, list[str]] = {}
        for key, minimum_count in cls.REQUIRED_WORLD_BUILDING_KEYS.items():
            values = payload.get(key)
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError(f"{cls.WORLD_BUILDING_PATH} key `{key}` must be a list of strings.")
            cleaned = [value.strip() for value in values if value.strip()]
            if len(cleaned) < minimum_count:
                raise ValueError(
                    f"{cls.WORLD_BUILDING_PATH} key `{key}` must contain at least {minimum_count} value(s)."
                )
            data[key] = cleaned

        return WorldBuildingData(
            races=data["races"],
            classes=data["classes"],
            pronouns=data["pronouns"],
            given_names=data["given_names"],
            family_names=data["family_names"],
            origins=data["origins"],
            motivations=data["motivations"],
        )

    @staticmethod
    def parse_model_markdown(response: str) -> dict[str, str]:
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        match = re.search(
            r"BACKSTORY:\s*(?P<backstory>.*?)\s*SUMMARY:\s*(?P<summary>.+)\s*$",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            preview = text.replace("\n", "\\n")[:500]
            raise ValueError(
                "Model response did not include BACKSTORY: and SUMMARY: sections. "
                f"Preview: {preview}"
            )
        return {
            "backstory": match.group("backstory").strip(),
            "summary": match.group("summary").strip(),
        }

    @staticmethod
    def normalize_backstory(backstory: str) -> str:
        paragraphs = [paragraph.strip() for paragraph in backstory.split("\n\n") if paragraph.strip()]
        return "\n\n".join(paragraphs)

    @staticmethod
    def draft_backstory(
        first_name: str,
        level: str,
        race: str,
        character_class: str,
        origin: str,
        motivations: list[str],
    ) -> str:
        first_motivation, second_motivation = motivations[:2]
        return (
            f"{first_name} grew up in {origin}, known less for heroic promise than for the small habits "
            f"that kept neighbors alive: mending gear before storms, remembering which doors stuck, "
            f"and listening when older travelers talked about roads that no longer appeared on maps.\n\n"
            f"Training as a level {level} {race} {character_class} came from necessity rather than glory. "
            f"{first_name} learned to survive mistakes, carry guilt without letting it steer every choice, "
            f"and read danger in the pauses between other people's words.\n\n"
            f"Now {first_name} adventures to {first_motivation} and to {second_motivation}. "
            "Those goals sometimes strengthen each other, giving every risk a practical reason, "
            "but they also compete whenever loyalty asks for patience and ambition demands speed."
        )

    @staticmethod
    def first_name(name: str) -> str:
        return name.strip().split()[0] if name.strip() else name

    @staticmethod
    def gender_from_pronouns(pronouns: str) -> str:
        if pronouns == "she/her":
            return "female"
        if pronouns == "he/him":
            return "male"
        return "non-binary"
