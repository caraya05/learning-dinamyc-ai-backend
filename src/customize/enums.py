from enum import Enum


class GenderType(Enum):
    MAN = "man"
    WOMAN = "woman"
    BOTH = "both"
    OTHER = "other"


class CustomizeType(Enum):
    CLOTHES = "clothes"
    HAIR = "hair"
    HEAD = "head"
    BODY = "body"
    UPPER_GARMENT = "upper garment"
    LOWER_GARMENT = "lower garment"
    SHOES = "shoes"
    BEARD = "beard"
    OTHER = "other"


class CharacterType(Enum):
    HUMAN = "human"
    ANIMAL = "animal"
    OTHER = "other"
