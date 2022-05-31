from os import getenv


class WarehouseIntegrationType:
    ONGOING = 1


class YaylohServices:
    RPLATFORM = getenv("RPLATFORM_URL")
