from enum import Enum

class MemoryComponent(str, Enum):

    DRAM = "DRAM"
    NAND = "NAND"
    DDR4 = "DDR4"
    DDR5 = "DDR5"
    LPDDR5 = "LPDDR5"
    HBM2E = "HBM2E"
    HBM3 = "HBM3"
    NAND_TLC = "NAND_TLC"
    NAND_QLC = "NAND_QLC"
    NAND_MLC = "NAND_MLC"

class MarketSegment(str, Enum):

    SERVER = "SERVER"
    CONSUMER = "CONSUMER"
    MOBILE = "MOBILE"
    AUTOMOTIVE = "AUTOMOTIVE"
    AI_ACCELERATOR = "AI_ACCELERATOR"
    ENTERPRISE_SSD = "ENTERPRISE_SSD"
    CONSUMER_SSD = "CONSUMER_SSD"

class PriceUnit(str, Enum):
    USD_PER_GB = "USD_PER_GB"
    USD_PER_UNIT = "USD_PER_UNIT"
    USD_PER_WAFER = "USD_PER_WAFER"

class DataSource(str, Enum):
    DRAMEXCHANGE = "DRAMEXCHANGE"
    TECHPOWERUP = "TECHPOWERUP"
    NEWEGG = "NEWEGG"
    AMAZON = "AMAZON"
    MANUAL = "MANUAL"
    SIMULATED = "SIMULATED"    