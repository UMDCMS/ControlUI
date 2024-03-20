import copy
import time
from typing import Any, Dict, Optional

import yaml
import zmq

from ..utils import merge_nested


class TBController(object):
    def __init__(
        self,
        ip: str,
        daq_port: int,
        pull_port: int,
        i2c_port: int,
        config_file: str,
        pull_ip="localhost",
    ):
        """
        @brief Setting up the various socket connections.

        The user should include the network settings required for the various
        sockets, as well as the "default" configuration file we should flush to
        the server sessions. One setting that we overwrite is have the data
        pulling socket have a to matching the IP address to the tileboard
        connect, as the original expected the data pulling client to run on the
        same machine that is hosting the data pulling server.
        """
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        self.daq_socket = DAQController(ip=ip, port=daq_port, config=config)
        self.i2c_socket = I2CController(ip=ip, port=i2c_port, config=config)
        self.pull_socket = DAQController(ip=pull_ip, port=pull_port, config=config)

        # Letting the data puller understand where to pull the data from.
        self.pull_socket.yaml_config["global"]["serverIP"] = ip


class ZMQController:
    """
    Base class for interacting with tileboard tester hardware as a ZMQ client.
    Here we are assuming that the host socket is already available on the
    tileboard tester.
    """

    def __init__(self, ip: str, port: int, config: Dict[str, Any]):
        self._ip = ip
        self._port = port
        self._config = copy.copy(config)
        # Creating the socket
        self.socket = zmq.Context().socket(zmq.REQ)
        self.socket.connect(f"tcp://{self._ip}:{self._port}")

    def socket_send(self, message: str) -> str:
        """
        Sending a message over the socket connection and returning the respond
        string. (No additional parsing).
        """
        self.socket.send_string(message)
        return self.socket.recv()

    def socket_check(self, message: str, check_str: str) -> bool:
        """
        Checking the response string on a message request for a particular
        substring. Using the str.find method, which returns -1 if substring was
        not found.
        """
        return self.socket_send(message).decode().lower().find(check_str.lower()) >= 0

    def configure(self, update_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Sending a yaml config string to socket connection.

        The return function will be the results of sending the configuration.
        If no YAML fragment is specified, then the entire configuration stored
        in the class instance is sent. If a YAML configuration fragment is
        specified, then the configuration updated in the main configuration
        instances as well.
        """
        if not self.socket_check("configure", "ready"):
            raise RuntimeError("Socket is not ready for configuration!")

        if update_config is None:
            update_config = self._config
        else:
            merge_nested(self._config, update_config)
        return self.socket_send(yaml.dump(update_config))


class I2CController(ZMQController):
    """
    Specialized ZMQController class for I2C slow controls
    """

    def __init__(self, ip: str, port: int, config: Dict[str, Any]):
        super().__init__(ip=ip, port=port, config=config)
        # Not sure when this is needed. not adding for the time being.
        # self.maskedDetIds = []
        if not self.socket_check("initialize", "ready"):
            raise RuntimeError(
                """
                I2C server did not receive a ready signal! Make sure the I2C
                slow control server has been started without error on the
                tileboard tester.
                """
            )
        self.configure()
        # TODO : Make this more human readable
        self.set_gbtsca_gpio_direction(0x0FFFFF9C)  # '0': input, '1': output
        self.set_gbtsca_gpio_vals(0x01 << 20, 0x11 << 20)
        self.set_gbtsca_gpio_vals(0x1 << 7, 0x1 << 7)
        self.set_gbtsca_gpio_vals(0x00000000, 0b11111111 << 8)

    def reset_tdc(self):
        """Resetting the TDC settings"""
        return yaml.safe_load(self.socket_send("resettdc"))

    def cont_i2c(self, target, *vals):
        """
        A typical pattern for either getting or setting I2C values is done by
        sending the a "set/read_<target> <val1> <val2>" request string to the I2C
        server, where values indicate the target channel/sub-channels or user input
        values. Here we provide a simple interface to generate the expression of
        interest.
        """
        return self.socket_send(" ".join([target, *[str(x) for x in vals]]))

    def get_sipm_voltage(self):
        return self.cont_i2c("read_sipm_voltage")

    def get_sipm_current(self):
        return self.cont_i2c("read_sipm_current")

    def get_led_voltage(self):
        return self.cont_i2c("read_led_voltage")

    def get_led_current(self):
        return self.cont_i2c("read_led_current")

    def set_led_dac(self, val):
        return self.cont_i2c("set_led_dac", val)

    def set_gbtsca_dac(self, dac, val):
        return self.cont_i2c("set_gbtsca_dac", dac, val)

    def read_gbtsca_dac(self, dac):
        return self.cont_i2c("read_gbtsca_dac", dac)

    def read_gbtsca_adc(self, channel):
        return self.cont_i2c("read_gbtsca_adc", channel)

    def read_gbtsca_gpio(self):
        return self.cont_i2c("read_gbtsca_gpio")

    def set_gbtsca_gpio_direction(self, direction):
        return self.cont_i2c("set_gbtsca_gpio_direction", direction)

    def get_gbtsca_gpio_direction(self):
        return self.cont_i2c("get_gbtsca_gpio_direction")

    def set_gbtsca_gpio_vals(self, vals, mask):
        return self.cont_i2c("set_gbtsca_gpio_vals", vals, mask)

    def MPPC_Bias(self, channel=1) -> float:
        """Reading out the SiPM bias voltage in units of Volts"""
        adc_val = self.read_gbtsca_adc(9 if channel == 1 else 10)
        # Additional multiplier for resistor divider changes between different in
        # tileboard version TODO: update when TB version 2 or version 3 is received.
        ad_mult = (82.0 / 1.0) / (200.0 / 4.0)
        return float(adc_val) / 4095 * 204000 / 4000 * ad_mult


class DAQController(ZMQController):
    """
    Specialization zmq messages for fast data and retrival nodes.
    """

    def start(self):
        """Starting a config file control sequence"""
        while not self.socket_check("start", "running"):
            time.sleep(0.1)

    def is_complete(self):
        """Checking whether then run sequence is complete"""
        return not self.socket_check("run_done", "notdone")

    def stop(self):
        """Ensuring the the signal has been stopped"""
        return self.socket_send("stop")

    def enable_fast_commands(self, **kwargs):
        self._config["daq"]["l1a_enables"].update(
            {
                "periodic_l1a_A": kwargs.get("A", 0),
                "periodic_l1a_B": kwargs.get("B", 0),
                "periodic_l1a_C": kwargs.get("C", 0),
                "periodic_l1a_D": kwargs.get("D", 0),
                "random_l1a": kwargs.get("random", 0),
                "external_l1a": kwargs.get("external", 0),
                "block_sequencer": kwargs.get("sequencer", 0),
                "periodic_ancillary": kwargs.get("ancillary", 0),
            }
        )

    def l1a_generator_settings(self, name="A", **kwargs):
        kwargs.setdefault("BX", 0x10)
        kwargs.setdefault("length", 43)
        kwargs.setdefault("cmdtype", "L1A")
        kwargs.setdefault("prescale", 0)
        kwargs.setdefault("followMode", "DISABLE")
        for gen in self.yaml_config["daq"]["l1a_generator_settings"]:
            if gen["name"] == name:
                gen.update(**kwargs)

    def l1a_settings(self, **kwargs):
        """Updating the L1 acquisition information"""
        self.yaml_config["daq"]["l1a_settings"].update(
            {
                "bx_spacing": kwargs.get("bx_spacing", 43),
                "external_debounced": kwargs.get("external_debounced", 0),
                "length": kwargs.get("length", 43),
                "ext_delay": kwargs.get("ext_delay", 0),
                "prescale": kwargs.get("prescale", 0),
                "log_rand_bx_period": kwargs.get("log_rand_bx_period", 0),
            },
        )
