"""The lane's reserved port, when the autopilot gives one, must be free to bind."""

import os
import socket
import unittest


class ReservedPortTest(unittest.TestCase):
    def test_reserved_port_is_bindable(self):
        port = os.environ.get("TASKRAIL_RESOURCE_PORT")
        if not port:
            self.skipTest("TASKRAIL_RESOURCE_PORT is not set")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", int(port)))


if __name__ == "__main__":
    unittest.main()
