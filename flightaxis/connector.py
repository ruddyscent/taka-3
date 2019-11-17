#!/usr/bin/env python3
""" Simulator connector for FlightAxis Link

Copyright (C) 2019  BioBrain, Inc

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import socket
import textwrap

import numpy as np

SIM_DEFAULT = { # (name, value, save)        
        "AHRS_EKF_TYPE": (10, False),
        "INS_GYR_CAL": (0, False),
        "RC1_MIN": (1000, True),
        "RC1_MAX": (2000, True),
        "RC2_MIN": (1000, True),
        "RC2_MAX": (2000, True),
        "RC3_MIN": (1000, True),
        "RC3_MAX": (2000, True),
        "RC4_MIN": (1000, True),
        "RC4_MAX": (2000, True),
        "RC2_REVERSED": (1, False), # interlink has reversed rc2
        "SERVO1_MIN": (1000, False),
        "SERVO1_MAX": (2000, False),
        "SERVO2_MIN": (1000, False),
        "SERVO2_MAX": (2000, False),
        "SERVO3_MIN": (1000, False),
        "SERVO3_MAX": (2000, False),
        "SERVO4_MIN": (1000, False),
        "SERVO4_MAX": (2000, False),
        "SERVO5_MIN": (1000, False),
        "SERVO5_MAX": (2000, False),
        "SERVO6_MIN": (1000, False),
        "SERVO6_MAX": (2000, False),
        "SERVO6_MIN": (1000, False),
        "SERVO6_MAX": (2000, False),
        "INS_ACC2OFFS_X": (0.001, False),
        "INS_ACC2OFFS_Y": (0.001, False),
        "INS_ACC2OFFS_Z": (0.001, False),
        "INS_ACC2SCAL_X": (1.001, False),
        "INS_ACC2SCAL_Y": (1.001, False),
        "INS_ACC2SCAL_Z": (1.001, False),
        "INS_ACCOFFS_X": (0.001, False),
        "INS_ACCOFFS_Y": (0.001, False),
        "INS_ACCOFFS_Z": (0.001, False),
        "INS_ACCSCAL_X": (1.001, False),
        "INS_ACCSCAL_Y": (1.001, False),
        "INS_ACCSCAL_Z": (1.001, False),
}

ACTION_FMT = {
    "RestoreOriginalControllerDevice":
    ("<?xml version='1.0' encoding='UTF-8'?>\n"
     "<soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' "
     "xmlns:xsd='http://www.w3.org/2001/XMLSchema' "
     "xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>\n"
     "<soap:Body>\n"
     "<RestoreOriginalControllerDevice><a>1</a><b>2</b>"
     "</RestoreOriginalControllerDevice>\n"
     "</soap:Body>\n"
     "</soap:Envelope>"),
    "InjectUAVControllerInterface":
    ("<?xml version='1.0' encoding='UTF-8'?> "
     "<soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' "
     "xmlns:xsd='http://www.w3.org/2001/XMLSchema' "
     "xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'> "
     "<soap:Body> "
     "<InjectUAVControllerInterface><a>1</a><b>2</b>"
     "</InjectUAVControllerInterface> "
     "</soap:Body> "
     "</soap:Envelope>"),
    "ExchangeData":
    ("<?xml version='1.0' encoding='UTF-8'?> "
     "<soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' "
     "xmlns:xsd='http://www.w3.org/2001/XMLSchema' "
     "xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'> "
     "<soap:Body> "
     "<ExchangeData> "
     "<pControlInputs> "
     "<m-selectedChannels>4095</m-selectedChannels> "
     "<m-channelValues-0to1> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "<item>{:.4f}</item> "
     "</m-channelValues-0to1> "
     "</pControlInputs> "
     "</ExchangeData> "
     "</soap:Body> "
     "</soap:Envelope>"),
}


class FlightAxisConnector(object):
    """Simulator connector for FlightAxis Link

    """

    _URL = "biobrain.tplinkdns.com"
    _PORT = 18083
    _msg = ("POST / HTTP/1.1\n"
            "soapaction: '{}'\n"
            "content-length: {}\n"
            "content-type: text/xml;charset='UTF-8'\n"
            "Connection: Keep-Alive\n"
            "\n"
            "{}")

    def __init__(self):
        self._host_ip = socket.gethostbyname(
            FlightAxisConnector._URL)  # type: str
        self._socket = socket.socket(socket.AF_INET,
                                     socket.SOCK_STREAM)  # type: socket.socket
        # self._socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        # self._host_ip = "127.0.0.1"
        self._socket.connect((self._host_ip, FlightAxisConnector._PORT))
        self._socket.setblocking(0)
        self._socket.settimeout(1)

        # self._socket.bind(
        #    ("biobrain.tplinkdns.com", FlightAxisConnector._PORT))
        # self._socket.listen()
        # conn, addr = s.accept()
        # with conn:
        #     print('Connected by', addr)
        #     while True:
        #         data = conn.recv(1024)
        #         if not data:
        #             break
        #         print(data)
        self.servos = np.ones(12, dtype=float)

    def soap_request(self, action: str, fmt: str) -> str:
        """

        Args:
            action:
                "RestoreOriginalControllerDevice"
                "InjectUAVControllerInterface"
                "ExchangeData"
        Returns:
            Return string from RealFlight.
        """
        print(action)
        msg = FlightAxisConnector._msg.format(action, len(fmt), fmt)
        # ret = self._socket.send(bytes(msg, encoding="utf_8"))
        ret = self._socket.send(msg.encode("utf_8", errors="strict"))
        #print(bytes(msg, encoding="utf8"))
        print(msg)
        #print(ret)

        data = self._socket.recv(10000).decode()
        return data


if __name__ == "__main__":
    fac = FlightAxisConnector()

    # action = "RestoreOriginalControllerDevice"
    # print(fac.soap_request(action, ACTION_FMT[action]))

    action = "InjectUAVControllerInterface"
    print(fac.soap_request(action, ACTION_FMT[action]))

    action = "ExchangeData"
    print(fac.soap_request(action, ACTION_FMT[action].format(*fac.servos)))
