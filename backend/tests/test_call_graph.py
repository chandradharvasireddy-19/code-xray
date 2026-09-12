from backend.app.analyzer.call_graph import CallGraphBuilder
from backend.app.analyzer.parser import SourceParser


def test_build_call_graph():
    code1 = """
class Controller:
    def process(self):
        PaymentService.process()
"""
    code2 = """
class PaymentService:
    def process(self):
        Database.save()

class Database:
    def save(self):
        pass
"""
    parser = SourceParser()
    pf1 = parser.parse_source(code1, file_path="controller.py")
    pf2 = parser.parse_source(code2, file_path="payment.py")

    builder = CallGraphBuilder()
    cg = builder.build([pf1, pf2])

    assert cg.node_count >= 3
    assert cg.edge_count >= 2


def test_get_callers_and_callees():
    code = """
def alpha():
    beta()

def beta():
    gamma()

def gamma():
    pass
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="chain.py")

    builder = CallGraphBuilder()
    cg = builder.build([pf])

    assert cg.get_callees("alpha") == ["beta"]
    assert cg.get_callees("beta") == ["gamma"]
    assert cg.get_callees("gamma") == []

    assert cg.get_callers("gamma") == ["beta"]
    assert cg.get_callers("beta") == ["alpha"]
    assert cg.get_callers("alpha") == []


def test_get_connected_files():
    code_a = """
from file_b import func_b
def func_a():
    func_b()
"""
    code_b = """
def func_b():
    pass
"""
    parser = SourceParser()
    pf_a = parser.parse_source(code_a, file_path="module_a.py")
    pf_b = parser.parse_source(code_b, file_path="module_b.py")

    builder = CallGraphBuilder()
    cg = builder.build([pf_a, pf_b])

    connected = cg.get_connected_files()
    assert ("module_a.py", "module_b.py") in connected


def test_get_relationships_metadata():
    code = """
def execute():
    target_function()
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="exec.py")

    cg = CallGraphBuilder().build([pf])
    rels = cg.get_relationships()

    assert len(rels) == 1
    rel = rels[0]
    assert rel.caller == "execute"
    assert rel.callee == "target_function"
    assert rel.file_path == "exec.py"
    assert rel.line_number == 3


def test_unresolved_or_unknown_calls():
    code = """
def dynamic_caller():
    external_library.run()
    unknown_func()
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="dynamic.py")

    cg = CallGraphBuilder().build([pf])

    callees = cg.get_callees("dynamic_caller")
    assert "external_library.run" in callees
    assert "unknown_func" in callees
