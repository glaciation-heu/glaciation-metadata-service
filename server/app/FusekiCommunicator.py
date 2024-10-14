from typing import Literal, Tuple

from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from SPARQLWrapper import JSON, SPARQLWrapper2
from SPARQLWrapper.SmartWrapper import Bindings
from SPARQLWrapper.Wrapper import QueryResult

# from typing import List, Dict, Any

# The `FusekiCommunicator` class is a Python class that provides methods for
# communicating with a Fuseki server using SPARQL queries.


class FusekiCommunicatior:
    def __init__(
        self, fuseki_url: str, port: int | str | None, dataset_name: str
    ) -> None:
        """
        The function initializes a SPARQLWrapper2 object with the provided Fuseki URL,
        port, and dataset name.

        :param fuseki_url: The `fuseki_url` parameter is a string that represents the
        URL of the Fuseki server. Fuseki is a SPARQL server that provides a web
        interface to query and manage RDF data
        :type fuseki_url: str
        :param port: The `port` parameter is the port number on which the Fuseki server
        is running. It can be either an integer or a string representing the port number
        :type port: int | str
        :param dataset_name: The `dataset_name` parameter is a string that represents
        the name of the dataset in Fuseki. Fuseki is a SPARQL server that provides a way
        to query and manipulate RDF data. The `dataset_name` parameter is used to
        specify which dataset you want to interact with in Fuseki
        :type dataset_name: str
        """
        self.fuseki_url = fuseki_url
        self.port = port
        self.dataset_name = dataset_name

        port_placeholder = f":{self.port}" if self.port is not None else ""
        self.sparql = SPARQLWrapper2(
            "http://{}{}/{}".format(
                self.fuseki_url, port_placeholder, self.dataset_name
            )
        )
        self.sparql.method = "POST"

    def validate_sparql(
        self, query: str, query_type: Literal["query", "update"]
    ) -> Tuple[bool, str]:
        parser = parseQuery if query_type == "query" else parseUpdate
        try:
            parser(query)
            return True, "The SPARQL query is syntactically correct."
        except Exception as e:
            return False, f"Syntax error in query: {e}"

    def read_query(self, query: str) -> Bindings | QueryResult | None:
        """
        The function reads a SPARQL query, sets it as the query for a SPARQL object, and
        returns the result of the query as a list of dictionaries, a single value, or
        None if an exception occurs.

        :param query: The `query` parameter is a string that represents the SPARQL query
        that you want to execute. SPARQL is a query language for querying RDF data
        :type query: str
        """
        self.sparql.setQuery(query)
        self.sparql.setReturnFormat(JSON)
        try:
            return self.sparql.query()
        except Exception as e:
            print(e)
            return None

    def update_query(self, query: str) -> Bindings | QueryResult | None:
        self.sparql.setQuery(query)
        try:
            return self.sparql.query()
        except Exception as e:
            print(e)
            return None
