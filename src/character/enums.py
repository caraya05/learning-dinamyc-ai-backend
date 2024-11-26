from enum import Enum


class TypeCharacter(Enum):
    LEADING_ROLE = "leading role"
    ENEMY = "enemy"
    NPC = "npc"
    # ANTAGONIST = "antagonist"
    # OTHER = "other"
    # MINI_ENEMY = "mini enemy"


class GenderCharacter(Enum):
    MAN = "man"
    WOMAN = "woman"


class TypeConversation(Enum):
    NONE_CONVERSATION = "none"
    ONE_WAY_CONVERSATION = "one_way "
    TWO_WAY_CONVERSATION = "two_way "
