"""Every part GPiBridge uses, in one place.

The schematic takes symbols, footprints, values and LCSC codes from here; the
library is built from the symbols and footprints named here; the BOM and the
checks read it.  A part's LCSC code must name exactly the part described:
tools/check_parts.py compares each code's JLCPCB description with `match`
(every word of it must appear) before a release is made.

Fields:
  sym      symbol in the project library (GPiBridge:...)
  fp       footprint in the project library
  lcsc     LCSC/JLCPCB code, None for a part JLCPCB does not place
  mpn      manufacturer part number
  value    what the schematic and silkscreen print
  match    words JLCPCB's description of `lcsc` must contain
  note     why this part (shown in the BOM)
"""

LIB = "GPiBridge"


def P(sym, fp, lcsc, mpn, value, match, note=""):
    return dict(sym=LIB + ":" + sym, fp=LIB + ":" + fp, lcsc=lcsc, mpn=mpn, value=value,
                match=match, note=note)


PARTS = {
    # --- the chips ---------------------------------------------------------
    "RP2354A": P("RP2354A", "RP2350A_QFN-60_7x7mm_P0.4mm_RPi", "C41378174", "RP2354A", "RP2354A",
                 ["RP2354A", "QFN-60"], "RP2350 with 2 MB flash stacked in the package"),
    "SN75160B": P("SN75160B", "SOIC-20W_7.5x12.8mm_P1.27mm", "C882412", "SN75160BDWR", "SN75160B",
                  ["SN75160BDWR", "SOIC-20"], "IEEE-488 data transceiver (DIO1-8)"),
    "SN75161B": P("SN75161B", "SOIC-20W_7.5x12.8mm_P1.27mm", "C2671348", "SN75161BDWR", "SN75161B",
                  ["SN75161BDWR", "SOIC-20"], "IEEE-488 control transceiver, single controller"),
    "XC6206": P("XC6206P332MR", "SOT-23-3", "C5446", "XC6206P332MR-G", "XC6206 3.3V",
                ["XC6206P332MR", "3.3V", "SOT-23"], "3.3 V LDO, 200 mA; the board draws about 50 mA from it"),
    "AO3401A": P("AO3401A", "SOT-23", "C15127", "AO3401A", "AO3401A",
                 ["AO3401A", "P-Channel"], "P-MOSFET that switches 5 V to the transceivers"),
    "2N7002": P("2N7002", "SOT-23", "C8545", "2N7002", "2N7002",
                ["2N7002", "N-Channel"], "pulls the AO3401A's gate down when the firmware asks"),
    # --- clock, regulator, connectors, controls ----------------------------
    "Y12M": P("Crystal_GND24", "Crystal_SMD_3225-4Pin_3.2x2.5mm", "C20625731", "ABM8-272-T3", "12MHz",
              ["ABM8-272-T3", "12MHz"], "the crystal Raspberry Pi specifies for the RP2350"),
    "L3U3": P("L", "L_Abracon_AOTA-B201610_RPi", "C42411119", "AOTA-B201610S3R3-101-T", "3.3uH",
              ["AOTA-B201610S3R3-101-T"], "polarity-marked inductor for the RP2350's core regulator"),
    "USBC": P("USB_C_Receptacle_USB2.0_16P", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948",
              "TYPE-C-31-M-12", "USB-C", ["TYPE-C-31-M-12"], "built right on the Lorenz board; datum known"),
    "JSTSH3": P("Conn_Debug_3", "JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical", "C160389",
                "BM03B-SRSS-TB(LF)(SN)", "SH 1x3", ["BM03B-SRSS-TB"],
                "Raspberry Pi debug connector, genuine JST, top entry through openings in the lid"),
    "BUTTON": P("SW_Push", "SW_SPST_TS-1088-xR020", "C720477", "TS-1088-AR02016", "BOOT",
                ["TS-1088-AR02016"], "BOOTSEL, for recovery only"),
    "GPIB": dict(sym=LIB + ":IEEE488_Plug", fp=LIB + ":IEEE488_Plug_24P_P2.16mm_DIP_Solder", lcsc=None,
                 mpn="NorComp 111-024-113L001, or any 24-pin IEEE-488 male, DIP solder, 2.16 mm pitch",
                 value="IEEE-488", match=[],
                 note="hand-soldered after assembly: JLCPCB does not stock it"),
    # --- LEDs -----------------------------------------------------------------
    "LED_Y": P("LED", "LED_0805_2012Metric", "C2296", "KT-0805Y", "yellow", ["KT-0805Y", "0805"],
               "low forward voltage, so a 3.3 V pin can drive it"),
    "LED_R": P("LED", "LED_0805_2012Metric", "C84256", "NCD0805R1", "red", ["NCD0805R1", "0805"],
               "low forward voltage, so a 3.3 V pin can drive it"),
    "LED_G": P("LED", "LED_0805_2012Metric", "C2297", "KT-0805G", "green", ["KT-0805G", "0805"],
               "on the 5 V transceiver rail, so its 2.6-3.1 V drop does not matter"),
}


def passive(kind, value, size, lcsc, mpn, match, note=""):
    sym = {"R": "R", "C": "C"}[kind]
    fp = {("R", "0402"): "R_0402_1005Metric", ("C", "0402"): "C_0402_1005Metric",
          ("R", "0603"): "R_0603_1608Metric", ("C", "0603"): "C_0603_1608Metric",
          ("C", "0402RPi"): "C_0402_RPi", ("C", "0402RPiWide"): "C_0402_RPi_wide",
          ("R", "0402RPi"): "R_0402_RPi"}[(kind, size)]
    return P(sym, fp, lcsc, mpn, value, match, note)


PARTS.update({
    # capacitors
    "C100N": passive("C", "100n", "0402", "C1525", "CL05B104KO5NNNC", ["100nF", "0402"]),
    "C10N": passive("C", "10n", "0402", "C15195", "CL05B103KB5NNNC", ["10nF", "0402"]),
    "C15P": passive("C", "15p", "0402", "C1548", "0402CG150J500NT", ["15pF", "C0G", "0402"]),
    "C1U": passive("C", "1u", "0402", "C52923", "CL05A105KA5NQNC", ["1uF", "25V", "0402"]),
    "C10U": passive("C", "10u", "0603", "C19702", "CL10A106KP8NNNC", ["10uF", "0603"]),
    # Raspberry Pi's own footprints for the core regulator's parts, so their
    # layout can be copied exactly (gen/rpi_minimal/)
    "C4U7_RPI_WIDE": passive("C", "4.7u", "0402RPiWide", "C23733", "CL05A475MP5NRNC", ["4.7uF", "0402"]),
    "C4U7_RPI": passive("C", "4.7u", "0402RPi", "C23733", "CL05A475MP5NRNC", ["4.7uF", "0402"]),
    "R33_RPI": passive("R", "33", "0402RPi", "C25105", "0402WGF330JTCE", ["33Ω", "0402"]),
    # resistors
    "R27": passive("R", "27", "0402", "C25100", "0402WGF270JTCE", ["27Ω", "0402"],
                   "USB series resistors: RP2350 datasheet, 27 ohms; 0402 as in Raspberry Pi's layout"),
    "R100": passive("R", "100", "0402", "C25076", "0402WGF1000TCE", ["100Ω", "0402"]),
    "R330": passive("R", "330", "0402", "C25104", "0402WGF3300TCE", ["330Ω", "0402"]),
    "R1K": passive("R", "1k", "0402", "C11702", "0402WGF1001TCE", ["1kΩ", "0402"]),
    "R1K5": passive("R", "1.5k", "0402", "C25867", "0402WGF1501TCE", ["1.5kΩ", "0402"]),
    "R4K7": passive("R", "4.7k", "0402", "C25900", "0402WGF4701TCE", ["4.7kΩ", "0402"]),
    "R5K1": passive("R", "5.1k", "0402", "C25905", "0402WGF5101TCE", ["5.1kΩ", "0402"]),
    "R10K": passive("R", "10k", "0402", "C25744", "0402WGF1002TCE", ["10kΩ", "0402"]),
    "R100K": passive("R", "100k", "0402", "C25741", "0402WGF1003TCE", ["100kΩ", "0402"]),
    # not placed by JLCPCB
    "TP": dict(sym=LIB + ":TestPoint", fp=LIB + ":TestPoint_Pad_D1.0mm", lcsc=None, mpn="", value="",
               match=[], note="bare pad"),
    "PWR_FLAG": dict(sym=LIB + ":PWR_FLAG", fp=LIB + ":", lcsc=None, mpn="", value="PWR_FLAG", match=[],
                     note="tells ERC where a rail is driven from"),
    "HOLE": dict(sym=LIB + ":MountingHole", fp=LIB + ":MountingHole_2.2mm_M2", lcsc=None, mpn="",
                 value="", match=[], note="M2 screw into the housing"),
})
