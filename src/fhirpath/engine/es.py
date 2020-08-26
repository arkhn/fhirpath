# _*_ coding: utf-8 _*_
import re
from typing import Optional
from zope.interface import implementer

from fhirpath.engine import EngineResultRow
from fhirpath.engine.base import (
    Engine,
    EngineResult,
    EngineResultBody,
    EngineResultHeader,
)
from fhirpath.enums import EngineQueryType
from fhirpath.interfaces import IElasticsearchEngine
from fhirpath.utils import BundleWrapper

CONTAINS_INDEX_OR_FUNCTION = re.compile(r"[a-z09_]+(\[[0-9]+\])|(\([0-9]*\))$", re.I)
CONTAINS_INDEX = re.compile(r"[a-z09_]+\[[0-9]+\]$", re.I)
CONTAINS_FUNCTION = re.compile(r"[a-z09_]+\([0-9]*\)$", re.I)

__author__ = "Md Nazrul Islam<email2nazrul@gmail.com>"


@implementer(IElasticsearchEngine)
class ElasticsearchEngine(Engine):
    """Elasticsearch Engine"""

    def get_index_name(self, resource_type: Optional[str] = None):
        """ """
        raise NotImplementedError

    def get_mapping(self, resource_type):
        """ """
        raise NotImplementedError

    def _add_result_headers(self, query, result, compiled):
        """ """
        # Process additional meta
        result.header.raw_query = self.connection.finalize_search_params(compiled)
        result.header.selects = [w.path._raw for w in query.get_where()]

    def _execute(self, query, unrestricted, query_type):
        """ """
        query_copy = query.clone()

        if unrestricted is False:
            self.build_security_query(query_copy)

        compiled = self.dialect.compile(
            query_copy,
            calculate_field_index_name=self.calculate_field_index_name,
            get_mapping=self.get_mapping,
        )
        if query_type == EngineQueryType.DML:
            raw_result = self.connection.fetch(self.get_index_name(), compiled)
        elif (
            query_type == EngineQueryType.COUNT
        ):  # TODO can we use that for _summary=count?
            raw_result = self.connection.count(self.get_index_name(), compiled)
        else:
            raise NotImplementedError

        return raw_result, compiled

    def execute(self, query, unrestricted=False, query_type=EngineQueryType.DML):
        """ """
        raw_result, compiled = self._execute(query, unrestricted, query_type)

        # xxx: process result
        result = self.process_raw_result(raw_result, query_type)

        # Process additional meta
        self._add_result_headers(query, result, compiled)
        return result

    def build_security_query(self, query):
        """ """
        pass

    def calculate_field_index_name(self, resource_type):
        raise NotImplementedError

    def extract_hits(self, hits, container, doc_type="_doc"):
        """ """
        for res in hits:
            if res["_type"] != doc_type:
                continue
            row = EngineResultRow()

            # the res["_source"] object contains the resource data indexed by resource type.
            # eg: {"Patient": {patient_data...}}
            # this object should always have a single key:value pair since the term queries
            # performed by ES are always scoped by resource_type.
            # In short, row is an array with a single item.
            for resource_type, resource_data in res["_source"].items():
                row.append(resource_data)

            container.add(row)

    def process_raw_result(self, rawresult, query_type):
        """ """
        if query_type == EngineQueryType.COUNT:
            total = rawresult["count"]
        # let´s make some compabilities
        elif isinstance(rawresult["hits"]["total"], dict):
            total = rawresult["hits"]["total"]["value"]
        else:
            total = rawresult["hits"]["total"]

        result = EngineResult(
            header=EngineResultHeader(total=total), body=EngineResultBody()
        )
        # extract primary data
        if query_type != EngineQueryType.COUNT:
            self.extract_hits(rawresult["hits"]["hits"], result.body)

        if "_scroll_id" in rawresult and result.header.total > len(
            rawresult["hits"]["hits"]
        ):
            # we need to fetch all!
            consumed = len(rawresult["hits"]["hits"])

            while result.header.total > consumed:
                # xxx: dont know yet, if from_, size is better solution
                raw_res = self.connection.scroll(rawresult["_scroll_id"])
                if len(raw_res["hits"]["hits"]) == 0:
                    break

                self.extract_hits(raw_res["hits"]["hits"], result.body)

                consumed += len(raw_res["hits"]["hits"])

                if result.header.total <= consumed:
                    break

        return result

    def current_url(self):
        """
        complete url from current request
        return yarl.URL"""
        raise NotImplementedError

    def wrapped_with_bundle(self, result, includes):
        """ """
        url = self.current_url()
        wrapper = BundleWrapper(self, result, includes, url, "searchset")
        return wrapper()
