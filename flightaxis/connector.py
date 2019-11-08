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
    textwrap.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?> 
                    <soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
                    <soap:Body>
                    <RestoreOriginalControllerDevice><a>1</a><b>2</b></RestoreOriginalControllerDevice>
                    </soap:Body>
                    </soap:Envelope>)"""),
    "InjectUAVControllerInterface":
    textwrap.dedent("""\
                    <?xml version='1.0' encoding='UTF-8'?> i
                    <soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'> 
                    <soap:Body> 
                    <InjectUAVControllerInterface><a>1</a><b>2</b></InjectUAVControllerInterface> 
                    </soap:Body> 
                    </soap:Envelope>"""),
    "ExchangeData":
    textwrap.dedent("""\
                    (<?xml version='1.0' encoding='UTF-8'?>
                    <soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope/' xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
                    <soap:Body>
                    <ExchangeData>
                    <pControlInputs>
                    <m-selectedChannels>4095</m-selectedChannels>
                    <m-channelValues-0to1>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <ite>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    <item>%.4f</item>
                    </m-channelValues-0to1>
                    </pControlInputs>
                    </ExchangeData>
                    </soap:Body>
                    </soap:Envelope>)"""),
}


class FlightAxisConnector(object):
    """Simulator connector for FlightAxis Link

    """

    _URL = "biobrain.tplinkdns.com"
    _PORT = 18083
    _msg = f"(POST / HTTP/1.1 \
            soapaction: %s \
            content-length: %s \
            content-type: text/xml;charset='UTF-8' \
            connection: keep-alive \
            \
            %s)"

    def __init__(self):
        self._host_ip = socket.gethostbyname(FlightAxis._URL)  # type: str
        self._s = socket.socket(socket.AF_INET,
                                socket.SOCK_STREAM)  # type: socket.socket
        self._s.connect((self._host_ip, FlightAxis._PORT))

        self.servo = np.zero(16, dtype=int)

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
        msg = FlightAxis._msg.format(action, len(fmt), fmt)
        return self._s.send(bytes(msg, encoding="utf8"))


if __name__ == "__main__":
    ax = FlightAxis()
    action = "InjectUAVControllerInterface"
    print(ax.soap_request(action, ax._action_fmt[action]))
    action = "RestoreOriginalControllerDevice"
    print(ax.soap_request(action, ax._action_fmt[action]))
