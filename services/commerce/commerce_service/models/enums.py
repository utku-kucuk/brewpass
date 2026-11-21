import enum


class PlanCode(enum.StrEnum):
    SIP = "SIP"
    DAILY = "DAILY"
    BOTTOMLESS = "BOTTOMLESS"


class SubscriptionStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class DrinkSize(enum.StrEnum):
    S = "S"
    M = "M"
    L = "L"


class MilkOption(enum.StrEnum):
    NONE = "NONE"
    WHOLE = "WHOLE"
    SKIMMED = "SKIMMED"
    OAT = "OAT"
    ALMOND = "ALMOND"
    LACTOSE_FREE = "LACTOSE_FREE"


class OrderStatus(enum.StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
