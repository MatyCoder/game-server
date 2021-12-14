import unittest

from otp.networking import DownstreamClient, ToontownProtocol

class TestProtocol(ToontownProtocol):
    pass

class TestClient(DownstreamClient):
    upstreamProtocol = TestProtocol

class TestMessageDirector(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()