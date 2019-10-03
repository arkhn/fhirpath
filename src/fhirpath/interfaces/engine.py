# _*_ coding: utf-8 _*_
from zope.interface import Attribute
from zope.interface import Interface


__author__ = "Md Nazrul Islam<email2nazrul@gmail.com>"


class IEngine(Interface):
    """ """

    fhir_release = Attribute("FHIR Release")
    connection = Attribute("DB Connection")
    dialect = Attribute("Dialect")

    def execute():  # lgtm[py/not-named-self]
        """Return"""

    def connect(**kw):  # lgtm[py/not-named-self]
        """Return a new Connection object."""

    def wrapped_with_bundle():  # lgtm[py/not-named-self]
        """ """


class IElasticsearchEngine(IEngine):
    """ """

    def get_index_name(context):  # lgtm[py/not-named-self]
        """ """

    def build_security_query():  # lgtm[py/not-named-self]
        """ """

    def calculate_field_index_name():  # lgtm[py/not-named-self]
        """ """


class IEngineFactory(Interface):
    """Utility marker"""


class IElasticsearchEngineFactory(IEngineFactory):
    """ """
