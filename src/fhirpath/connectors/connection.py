# _*_ coding: utf-8 _*_
from zope.interface import implementer

from fhirpath.interfaces import IConnection
from fhirpath.thirdparty import Proxy

__author__ = "Md Nazrul Islam <email2nazrul@gmail.com>"


@implementer(IConnection)
class Connection(object):
    """ """

    def __init__(self, conn):
        """ """
        self._conn = conn

    @property
    def raw_connection(self):
        """ """
        return self._conn

    @classmethod
    def from_prepared(cls, conn):
        """Connection instance creation, using already prepared RAW connection"""
        # xxx: do any validation
        self = cls(conn)
        return self

    @classmethod
    def from_url(cls, url: str):
        """
        1.) may be use connector utilities
        2.) may be url parser
        """
        raise NotImplementedError

    @classmethod
    def from_config(cls, config: dict):
        """ """
        raise NotImplementedError

    def __proxy__(self):
        """ """
        return ConnectionProxy(self)


class ConnectionProxy(Proxy):
    """ """

    def __init__(self, obj):
        """ """
        super(ConnectionProxy, self).__init__()
        self.initialize(IConnection(obj))
