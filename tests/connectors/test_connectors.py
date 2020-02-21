# _*_ coding: utf-8 _*_
import pytest
from elasticsearch import Elasticsearch

from fhirpath.connectors import create_connection
from fhirpath.connectors.factory import pg
from tests._utils import IS_TRAVIS


__author__ = "Md Nazrul Islam <email2nazrul@gmail.com>"


def test_es_connection_creation(es):
    """ """
    host, port = es
    conn_str = "es://@{0}:{1}/".format(host, port)
    conn = create_connection(conn_str, Elasticsearch)

    assert conn.raw_connection.ping() is True


@pytest.mark.skipif(IS_TRAVIS, reason="ignore for travis environment")
def test_pg_connection_creation(fhirbase_pg):
    """ """
    host, port = fhirbase_pg
    conn_str = "pg://postgres:@{0}:{1}/fhir_db".format(host, port)
    connection = create_connection(conn_str)
    info = connection.server_info()
    assert info is not None


@pytest.mark.skipif(IS_TRAVIS, reason="ignore for travis environment")
def test_pg_connection_from_url(fhirbase_pg):
    """ """
    host, port = fhirbase_pg
    conn_str = "pg://postgres:@{0}:{1}/fhir_db".format(host, port)
    connection = pg.PostgresConnection.from_url(conn_str)
    info = connection.server_info()
    assert info is not None
