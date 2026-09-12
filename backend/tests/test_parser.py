from pathlib import Path
from backend.app.analyzer.parser import SourceParser


def test_parse_imports():
    code = """
import os
import requests
import numpy as np
from services.payment import PaymentService, process_payment
from .models import Item
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="app/views.py")

    assert len(pf.errors) == 0
    modules = [(imp.module, imp.name, imp.alias, imp.is_from_import) for imp in pf.imports]

    assert ("os", None, None, False) in modules
    assert ("requests", None, None, False) in modules
    assert ("numpy", None, "np", False) in modules
    assert ("services.payment", "PaymentService", None, True) in modules
    assert ("services.payment", "process_payment", None, True) in modules
    assert (".models", "Item", None, True) in modules


def test_parse_functions_and_arguments():
    code = """
def calculate_tax(amount, rate=0.05):
    return amount * rate

async def fetch_user_data(user_id):
    pass
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="utils.py")

    assert len(pf.functions) == 2

    func1 = next(f for f in pf.functions if f.name == "calculate_tax")
    assert func1.arguments == ["amount", "rate"]
    assert func1.is_async is False
    assert func1.is_method is False
    assert func1.class_name is None
    assert func1.line_number == 2

    func2 = next(f for f in pf.functions if f.name == "fetch_user_data")
    assert func2.arguments == ["user_id"]
    assert func2.is_async is True
    assert func2.is_method is False


def test_parse_classes_and_methods():
    code = """
class BaseHandler:
    pass

class PaymentController(BaseHandler):
    def __init__(self, service):
        self.service = service

    def process(self, request):
        return self.service.pay(request)
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="controllers.py")

    assert len(pf.classes) == 2

    cls = next(c for c in pf.classes if c.name == "PaymentController")
    assert cls.base_classes == ["BaseHandler"]
    assert "process" in cls.methods
    assert "__init__" in cls.methods

    # Check methods represented as functions with class_name
    methods = [f for f in pf.functions if f.is_method]
    assert len(methods) == 2
    for m in methods:
        assert m.class_name == "PaymentController"


def test_parse_function_calls():
    code = """
def standalone():
    helper()

class Worker:
    def execute(self):
        self.prepare()
        database.save(123)

standalone()
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="jobs.py")

    call_records = [(c.caller, c.callee) for c in pf.calls]

    # Caller within standalone function
    assert ("standalone", "helper") in call_records

    # Callers within class method
    assert ("Worker.execute", "self.prepare") in call_records
    assert ("Worker.execute", "database.save") in call_records

    # Module-level call
    assert ("<module>", "standalone") in call_records


def test_parse_syntax_error_resilience():
    broken_code = """
def broken_function(
    this is invalid syntax !!!
"""
    parser = SourceParser()
    pf = parser.parse_source(broken_code, file_path="broken.py")

    assert len(pf.errors) == 1
    err = pf.errors[0]
    assert err.file_path == "broken.py"
    assert err.line_number is not None
    assert err.error_message != ""
    assert len(pf.functions) == 0


def test_parse_files_from_disk(tmp_path: Path):
    good_file = tmp_path / "good.py"
    good_file.write_text("def hello(): pass\n", encoding="utf-8")

    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(:\n", encoding="utf-8")

    parser = SourceParser()
    results = parser.parse_files([good_file, bad_file], base_path=tmp_path)

    assert len(results) == 2

    # Good file parsed
    good_res = next(r for r in results if "good.py" in r.file_path)
    assert len(good_res.errors) == 0
    assert len(good_res.functions) == 1

    # Bad file recorded error without crashing
    bad_res = next(r for r in results if "bad.py" in r.file_path)
    assert len(bad_res.errors) == 1
