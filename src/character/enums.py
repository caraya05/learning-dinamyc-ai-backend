from enum import Enum


class TypeCharacter(Enum):
    LEADING_ROLE = "leading role"
    ENEMY = "enemy"
    ANTAGONIST = "antagonist"
    OTHER = "other"
    MINI_ENEMY = "mini enemy"


class GenderCharacter(Enum):
    MAN = "man"
    WOMAN = "woman"
