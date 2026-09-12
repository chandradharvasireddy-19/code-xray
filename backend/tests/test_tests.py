from backend.app.analyzer.parser import SourceParser
from backend.app.analyzer.tests import TestAnalyzer


def test_discover_pytest_functions():
    code = """
def test_authentication_success():
    assert True

def test_login_invalid_password():
    assert False

def helper_create_user():
    return {}
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="tests/test_auth.py")

    analyzer = TestAnalyzer()
    report = analyzer.analyze([pf])

    assert "pytest" in report.frameworks_detected
    test_names = [t.test_name for t in report.tests]
    assert "test_authentication_success" in test_names
    assert "test_login_invalid_password" in test_names
    assert "helper_create_user" not in test_names


def test_discover_unittest_testcase():
    code = """
import unittest

class UserManagementTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_user_creation(self):
        self.assertTrue(True)

    def test_user_deletion(self):
        self.assertTrue(True)

    def helper_method(self):
        pass
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="tests/test_users.py")

    analyzer = TestAnalyzer()
    report = analyzer.analyze([pf])

    assert "unittest" in report.frameworks_detected
    test_names = [t.test_name for t in report.tests]
    assert "test_user_creation" in test_names
    assert "test_user_deletion" in test_names
    assert "setUp" not in test_names
    assert "helper_method" not in test_names

    for t in report.tests:
        assert t.test_class == "UserManagementTestCase"
        assert t.framework == "unittest"


def test_referenced_symbols_extraction():
    code = """
from services.payment import PaymentService

def test_process():
    s = PaymentService()
    s.process(100)
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="tests/test_payment.py")

    analyzer = TestAnalyzer()
    report = analyzer.analyze([pf])

    assert len(report.tests) == 1
    test_info = report.tests[0]
    assert "s.process" in test_info.referenced_symbols or "PaymentService" in test_info.referenced_symbols


def test_no_tests_in_regular_code():
    code = """
def calculate_metrics():
    return 42

class MetricsService:
    def execute(self):
        pass
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="service.py")

    analyzer = TestAnalyzer()
    report = analyzer.analyze([pf])

    assert len(report.tests) == 0
    assert len(report.frameworks_detected) == 0


def test_static_nature_no_execution():
    code = """
def test_static():
    raise RuntimeError("This code should NOT be executed during static analysis")
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="tests/test_static.py")

    analyzer = TestAnalyzer()
    report = analyzer.analyze([pf])

    assert len(report.tests) == 1
    assert report.tests[0].test_name == "test_static"
