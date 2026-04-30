from typing import Any, Dict, List, Literal, Tuple

import io

import pyoxigraph
from loguru import logger
from rdflib import ConjunctiveGraph
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate


class GraphStore:
    def __init__(self, store_path: str | None = None) -> None:
        if store_path:
            self.store = pyoxigraph.Store(store_path)
            logger.info(f"Opened persistent graph store at {store_path}")
        else:
            self.store = pyoxigraph.Store()
            logger.warning(
                "STORE_PATH not configured; using in-memory store "
                "(data will not persist across restarts)"
            )

    def validate_sparql(
        self, query: str, query_type: Literal["query", "update"]
    ) -> Tuple[bool, str]:
        parser = parseQuery if query_type == "query" else parseUpdate
        try:
            parser(query)
            return True, "The SPARQL query is syntactically correct."
        except Exception as e:
            return False, f"Syntax error in query: {e}"

    def read_query(self, query: str) -> Dict[str, Any]:
        results = self.store.query(query)
        if not isinstance(results, pyoxigraph.QuerySolutions):
            raise ValueError(f"Expected a SELECT query, got {type(results).__name__}")
        variables = results.variables
        vars_list = [v.value for v in variables]
        bindings: List[Dict[str, Any]] = []
        for solution in results:
            item: Dict[str, Any] = {}
            for var in variables:
                val = solution[var]
                if val is None:
                    continue
                var_name = var.value
                if isinstance(val, pyoxigraph.NamedNode):
                    item[var_name] = {"type": "uri", "value": val.value}
                elif isinstance(val, pyoxigraph.BlankNode):
                    item[var_name] = {"type": "bnode", "value": val.value}
                elif isinstance(val, pyoxigraph.Literal):
                    entry: Dict[str, str] = {"type": "literal", "value": val.value}
                    if val.language:
                        entry["xml:lang"] = val.language
                    else:
                        entry["datatype"] = val.datatype.value
                    item[var_name] = entry
            bindings.append(item)
        return {"vars": vars_list, "bindings": bindings}

    def update_query(self, query: str) -> None:
        self.store.update(query)

    def ingest_jsonld(self, json_ld_str: str) -> int:
        # pyoxigraph has no JSON-LD parser; convert via rdflib first.
        # Named graph IRIs are preserved from the @id in the document.
        g = ConjunctiveGraph()
        g.parse(data=json_ld_str, format="json-ld")
        n_triples = len(g)
        nquads = g.serialize(format="nquads")
        self.store.load(
            input=io.StringIO(nquads),
            mime_type="application/n-quads",
        )
        return n_triples

    def optimize(self) -> None:
        self.store.optimize()
