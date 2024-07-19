import time
from dataclasses import dataclass
from typing import Annotated

from ..hw import TBController
from ..utils import to_yaml
from ..yaml_format import ProcedureResult, SingularResult
from ._procedure_base import ProcedureBase


@dataclass(kw_only=True)
class tb_slowcontrol(ProcedureBase):
    tb_version: Annotated[str, "Version string of tileboard"]
    overvolt: Annotated[str, "Overvolt value [V]"]

    def run(self, tbc: TBController) -> ProcedureResult:
        # Dictionary for storing the final results
        self.loginfo("Overvoltage value:", self.overvolt)
        slow_control_results = {}

        # Initial setups
        tbc.i2c_socket.set_gbtsca_gpio_direction(0x0FFFFF9C)  # '0': input, '1': output
        tbc.i2c_socket.set_gbtsca_gpio_vals(0x00200000, 0x00300000)
        tbc.i2c_socket.set_gbtsca_gpio_vals(
            0x00200000 if self.tb_version == "TB3_2" else 0x00100000, 0x00300000
        )
        tbc.i2c_socket.set_gbtsca_gpio_vals(0x00000080, 0x00000080)
        tbc.i2c_socket.set_gbtsca_gpio_vals(0x00000000, 0x0000FF00)

        # should give 0x1000Cf in normal operation with MPPC_BIAS1 ON
        self.loginfo(f"GPIO values are {hex(int(tbc.i2c_socket.read_gbtsca_gpio()))}")
        self.loginfo(
            f"GPIO directions are {hex(int(tbc.i2c_socket.get_gbtsca_gpio_direction()))}"
        )

        ##### Set GBT_SCA DACs for MPPC Bias Voltage (Reference)  ################
        self.loginfo(">>> Setting DACs values")
        slow_control_results["DAC"] = {}  # See method for additional lookup
        tbc.i2c_socket.set_gbtsca_dac("A", self.OV_DAC("A"))
        tbc.i2c_socket.set_gbtsca_dac("B", self.OV_DAC("B"))
        tbc.i2c_socket.set_gbtsca_dac("C", self.OV_DAC("C"))
        tbc.i2c_socket.set_gbtsca_dac("D", self.OV_DAC("D"))
        slow_control_results.update(
            {x: tbc.i2c_socket.read_gbtsca_dac(x) for x in ["A", "B", "C", "D"]}
        )
        self.loginfo(
            "Dac A/B/C/D values: "
            + "/".join(
                [str(slow_control_results["DAC"][x]) for x in ["A", "B", "C", "D"]]
            )
        )
        self.loginfo("Wait for voltage stabilization (5 seconds)")
        time.sleep(5)

        ## This requires a new function!!!
        self.loginfo(">>> Reading ADC values")
        slow_control_results["temperature"] = {}
        for sca_channel in range(8):
            temp = tbc.i2c_socket.get_sca_temperature(sca_channel)
            slow_control_results["temperature"][f"T{sca_channel}"] = temp

        def adc_to_val(channel, scale, round=3):
            return round(
                float(tbc.i2c_socket.read_gbtsca_adc(channel)) / 4095 * scale, round
            )

        __ADC_DICT__ = {
            # Value name: (channel, scaling, rounding)
            "MPPC_BIAS1": (9, 204000 / 4000, 4),
            "MPPC_BIAS2": (10, 204000 / 4000, 4),
            "VCC_IN": (11, 15000 / 1000, 3),
            "LED_BIAS": (12, 15000 / 1000, 3),
            "VPA (+2.5V)": (13, 4000 / 1000, 3),
            "PRE_VPA (+3.5V)": (14, 4000 / 1000, 3),
            "VDDA": (15, 2000 / 1000, 3),
            "VDDD": (16, 2000 / 1000, 3),
            "PRE_VDDA": (17, 2000 / 1000, 3),
            "TB_ID0": (27, 1, 2),
            "TB_ID1": (28, 1, 2),
            "TB_ID2": (29, 1, 2),
        }

        for key, (channel, scale, round) in __ADC_DICT__.items():
            slow_control_results["ADC"][key] = adc_to_val(channel, scale, round)
            self.loginfo(f"ADC/{key}:{slow_control_results['ADC'][key]}")

        self.loginfo(">>>> Getting GPIO values")
        __GPIO_DICT__ = {
            # Key: (shift, nominal value)
            "ERROR": (0, 1),
            "PLL_LCK": (1, 1),
            "RSTB": (2, 1),
            "I2C_RSTB": (3, 1),
            "RESYNCLOAD": (4, 0),
            "SEL_CK_EXT": (6, 0),
            "LED_ON_OFF": (7, 1),
            "LED_DISABLE1": (8, 1),
            "LED_DISABLE2": (9, 1),
            "LED_DISABLE3": (10, 1),
            "LED_DISABLE4": (11, 1),
            "LED_DISABLE5": (12, 1),
            "LED_DISABLE6": (13, 1),
            "LED_DISABLE7": (14, 1),
            "LED_DISABLE8": (15, 1),
            "ENABLE_HV0": (20, 1),
            "ENABLE_HV1": (21, 1),
        }
        slow_control_results["GPIO"] = {}
        SCA_IOS = int(tbc.i2c_socket.read_gbtsca_gpio())
        for key, (shift, nominal) in __GPIO_DICT__:
            flag = (SCA_IOS & (0x1 << shift)) >> shift
            slow_control_results["GPIO"][key] = flag
            self.loginfo(f"{key} (nomial: {nominal}) = {flag}")

        # Writing readout results to file
        with self.open_text_file(
            "slow_control_readout.yaml", desc="Results of slow readout"
        ) as f:
            to_yaml(slow_control_results, f)

        # Writing final configuration to file
        with self.open_text_file(
            "slow_control_config.yaml", desc="Slow readout configuration"
        ) as f:
            to_yaml(tbc.i2c_socket._config, f)

        # Assuming to be successful if script complets
        self.result.board_summary = SingularResult(0, "SUCCESS")
        return self.result

    def OV_DAC(self, channel: str) -> int:
        # Dictionary for setting overvoltage? Should this not be global??
        __OV_lookup__ = {
            "TB2": {
                "2V": {"A": 180, "B": 125},
                "3V": {"A": 185, "B": 125},
                "3V5": {"A": 187, "B": 125},
                "4V": {"A": 190, "B": 125},
                "4V5": {"A": 193, "B": 125},
                "5V": {"A": 195, "B": 125},
                "5V5": {"A": 195, "B": 125},
                "6V": {"A": 200, "B": 125},
            },
            "TB2.1_2": {
                "2V": {"A": 193, "B": 120},
                "3V": {"A": 198, "B": 122},
                "3V5": {"A": 201, "B": 125},
                "4V": {"A": 203, "B": 122},
                "4V5": {"A": 206, "B": 125},
                "5V": {"A": 209, "B": 120},
                "5V5": {"A": 211, "B": 125},
                "6V": {"A": 213, "B": 122},
            },
            "TB2.1_3": {
                "1V": {"A": 192, "B": 121},
                "1V4": {"A": 192, "B": 121},
                "1V6": {"A": 193, "B": 121},
                "1V8": {"A": 194, "B": 122},
                "2V": {"A": 195, "B": 122},
                "2V2": {"A": 196, "B": 124},
                "3V": {"A": 200, "B": 124},
                "3V5": {"A": 203, "B": 125},
                "4V": {"A": 205, "B": 126},
                "4V5": {"A": 208, "B": 127},
                "5V": {"A": 210, "B": 128},
                "5V5": {"A": 213, "B": 129},
                "6V": {"A": 215, "B": 130},
            },
            "TB3_D8_1": {
                "0V9": {"A": 188, "B": 136},  # 40.5
                "1V": {"A": 189, "B": 134},  # 40.6
                "1V1": {"A": 190, "B": 132},  # 40.7
                "1V2": {"A": 191, "B": 130},  # 40.8
                "1V3": {"A": 192, "B": 128},  # 40.9
                "1V4": {"A": 193, "B": 126},  # 41.0
                "1V9": {"A": 196, "B": 122},  # correct, MPPC_BIAS1 = 41.5099
                "2V": {"A": 197, "B": 120},  # correct, MPPC_BIAS1 = 41.6095
                "2V1": {"A": 198, "B": 118},  # correct, MPPC_BIAS1 = 41.7092
                "2V2": {"A": 199, "B": 116},  # correct, MPPC_BIAS1 = 41.8337
                "2V3": {"A": 200, "B": 114},  # correct, MPPC_BIAS1 = 41.9209
                "2V4": {"A": 201, "B": 111},  # correct, MPPC_BIAS1 = 41.9956
                "2V5": {"A": 202, "B": 107},  # correct, MPPC_BIAS1 = 42.0205
                "2V6": {"A": 203, "B": 107},  # correct, MPPC_BIAS1 = 42.1949
                # 43.9 V, Aug 2023 test beam, MPPC_BIAS1 = 43.9 V ----------------Aug2023
                "4V": {"A": 210, "B": 118},
                "6V": {"A": 219, "B": 126},
                # 45.9 V  MPPC_BIAS1 =  45.9934, not corrected
            },
            "TB3_D8_2": {
                "2V": {"C": 183, "D": 122},
                "4V": {"C": 193, "D": 122},
            },
            "miniTB": {
                "4V": {"A": 1000, "B": 1000},  # 43.6 V
                "5V": {"A": 1000, "B": 1000},  # 44.6 V
                "6V": {"A": 1000, "B": 1000},  # 45.6 V
                "6V6": {"A": 1000, "B": 1000},  # 46.2 V
            },
            "TB3_G8_1": {
                #'1V':  {'A': 180, 'B': 127},  # 40.9 V  MPPC_BIAS1 =  40.8996
                "2V": {"A": 183, "B": 124},  # 41.9 V  MPPC_BIAS1 =  41.88
                "4V": {"A": 193, "B": 124},  # 43.9 V  MPPC_BIAS1 =  43.9136
                #'5V':  {'A': 202, 'B': 126},  # 44.9 V  MPPC_BIAS1 =  44.9348
                "6V": {"A": 207, "B": 110},  # 45.9 V  MPPC_BIAS1 =  46.6659
                #'6V6':  {'A': 210, 'B': 126},  # 46.5 V MPPC_BIAS1 =  46.4916
            },
            "TB3_G8_2": {
                #'1V':  {'A': 180, 'B': 127},  # 40.9 V  MPPC_BIAS1 =  40.8996
                "2V": {"A": 186, "B": 126},
                # 41.9 V  MPPC_BIAS1 =  41.896 ----------------Aug2023
                "4V": {"A": 197, "B": 124},
                # 43.9 V  MPPC_BIAS1 =  43.9385  --------------Aug2023
                #'5V':  {'A': 202, 'B': 126},  # 44.9 V  MPPC_BIAS1 =  44.9348
                "6V": {"A": 210, "B": 112},
                # 45.9 V  MPPC_BIAS1 =  45.956 ----------------Aug2023
                #'6V6':  {'A': 210, 'B': 126},  # 46.5 V MPPC_BIAS1 =  46.4916
            },
            "TB3_A5_1": {
                #'1V':  {'A': 180, 'B': 127},  # 40.9 V  MPPC_BIAS1 =  40.8996
                "2V": {"A": 190, "B": 122},
                # 41.9 V  MPPC_BIAS1 =  43.9385  --------------Aug2023
                "4V": {"A": 200, "B": 124},
                # 43.9 V  MPPC_BIAS1 =  41.896 ----------------Aug2023
                #'5V':  {'A': 202, 'B': 126},  # 44.9 V  MPPC_BIAS1 =  44.9348
                "6V": {"A": 211, "B": 122},
                # 45.9 V  MPPC_BIAS1 =  45.956 ----------------Aug2023
                #'6V6':  {'A': 210, 'B': 126},  # 46.5 V MPPC_BIAS1 =  46.4916
            },
        }

        if self.tb_version == "TB3_2":
            if channel == "A" or channel == "B":
                return 100
            else:
                return __OV_lookup__[self.tb_version][self.overvolt][channel]
        else:
            if channel == "C" or channel == "D":
                return 100
            else:
                return __OV_lookup__[self.tb_version][self.overvolt][channel]
