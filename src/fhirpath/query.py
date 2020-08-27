# _*_ coding: utf-8 _*_
from abc import ABC
from copy import copy
from typing import TYPE_CHECKING, List, Optional, Union

from zope.interface import implementer

from fhirpath.enums import EngineQueryType
from fhirpath.exceptions import ConstraintNotSatisfied, ValidationError
from fhirpath.model import Model
from fhirpath.thirdparty import Proxy
from fhirpath.utils import FHIR_VERSION, builder

from .constraints import (
    required_finalized,
    # required_from_resource,
    required_not_finalized,
)
from .exceptions import MultipleResultsFound
from .fql.expressions import and_, fql, sort_
from .fql.types import (
    ElementPath,
    ExcludeClause,
    FromClause,
    LimitClause,
    SelectClause,
    SortClause,
    WhereClause,
)
from .interfaces import (
    ICloneable,
    IElementPath,
    IGroupTerm,
    IQuery,
    IQueryBuilder,
    IQueryResult,
    ISortTerm,
    ITerm,
)

if TYPE_CHECKING:
    from fhirpath.engine.base import Engine

__author__ = "Md Nazrul Islam<email2nazrul@gmail.com>"


@implementer(IQuery, ICloneable)
class Query(ABC):
    """ """

    def __init__(
        self,
        fhir_release: FHIR_VERSION,
        from_: FromClause,
        select: SelectClause,
        exclude: ExcludeClause,
        where: WhereClause,
        sort: SortClause,
        limit: LimitClause,
    ):
        """ """

        self.fhir_release: FHIR_VERSION = FHIR_VERSION.normalize(fhir_release)
        self._from: FromClause = from_
        self._select: SelectClause = select
        self._exclude: ExcludeClause = exclude
        self._where: WhereClause = where
        self._sort: SortClause = sort
        self._limit: LimitClause = limit

    @classmethod
    def _builder(cls, engine: Optional["Engine"] = None) -> "QueryBuilder":
        return QueryBuilder(engine)

    @classmethod
    def from_builder(cls, builder: "QueryBuilder") -> "Query":
        """Create Query object from QueryBuilder.
        Kind of reverse process"""
        if not IQueryBuilder(builder)._finalized:
            raise ConstraintNotSatisfied("QueryBuilder object must be in finalized state")
        query = cls(
            builder._engine.fhir_release,  # type: ignore
            builder._from,  # type: ignore
            builder._select,  # type: ignore
            builder._exclude,  # type: ignore
            builder._where,  # type: ignore
            builder._sort,  # type: ignore
            builder._limit,  # type: ignore
        )
        return query

    def get_where(self) -> WhereClause:
        """ """
        return self._where

    def get_from(self) -> FromClause:
        """ """
        return self._from

    def get_select(self) -> SelectClause:
        """ """
        return self._select

    def get_exclude(self) -> ExcludeClause:
        """ """
        return self._exclude

    def get_sort(self) -> SortClause:
        """ """
        return self._sort

    def get_limit(self) -> LimitClause:
        """ """
        return self._limit

    def clone(self) -> "Query":
        """ """
        return self.__copy__()

    def __copy__(self) -> "Query":
        """ """
        newone = type(self).__new__(type(self))
        newone.__dict__.update(self.__dict__)

        newone.fhir_release = self.fhir_release

        newone._from = copy(self._from)
        newone._select = copy(self._select)
        newone._where = copy(self._where)
        newone._sort = copy(self._sort)
        newone._limit = copy(self._limit)

        return newone

    def __proxy__(self):
        """ """
        proxied = Proxy().initialize(self)
        return proxied


@implementer(IQueryBuilder)
class QueryBuilder(ABC):
    """ """

    def __init__(self, engine: Optional["Engine"] = None):
        """ """
        self._engine: Optional["Engine"] = engine
        self._finalized: bool = False

        self._from: FromClause = FromClause()
        self._select: SelectClause = SelectClause()
        self._exclude: ExcludeClause = ExcludeClause()
        self._where: WhereClause = WhereClause()
        self._sort: SortClause = SortClause()
        self._limit: LimitClause = LimitClause()

    def bind(self, engine: "Engine"):
        """ """
        # might be clone
        self._engine = engine

    def clone(self) -> "QueryBuilder":
        """ """
        return self.__copy__()

    def finalize(self, engine: Optional["Engine"] = None):
        """ """
        self._pre_check()

        if engine:
            self.bind(engine)

        if self._engine is None:
            raise ConstraintNotSatisfied(
                "Object from '{0!s}' must be binded with engine".format(self.__class__.__name__)
            )
        # xxx: do any validation?
        if len(self._select) == 0:
            el_path = ElementPath("*")
            self._select.append(el_path)

        # Finalize path elements
        [se.finalize(self._engine) for se in self._select]

        # Finalize excluded elements
        [se.finalize(self._engine) for se in self._exclude]

        # Finalize where terms on demand
        [wr.finalize(self._engine) for wr in self._where]

        # Finalize sorts ondemand
        [sr.finalize(self._engine) for sr in self._sort]

        self._validate()

        self._finalized = True

    def __copy__(self) -> "QueryBuilder":
        """ """
        newone = type(self).__new__(type(self))
        newone.__dict__.update(self.__dict__)

        newone._finalized = self._finalized
        newone._engine = self._engine

        newone._limit = copy(self._limit)
        newone._from = copy(self._from)
        newone._select = copy(self._select)
        newone._exclude = copy(self._exclude)
        newone._where = copy(self._where)
        newone._sort = copy(self._sort)

        return newone

    @builder
    def from_(self, resource_types: List[str]):
        """ """
        required_not_finalized(self)

        assert self._engine
        for resource_type in resource_types:
            model = Model.create(resource_type, fhir_release=self._engine.fhir_release)
            self._from.append((resource_type, model))

    @builder
    def select(self, *args):
        """ """
        self._pre_check()

        for el_path in args:
            if not IElementPath.providedBy(el_path):
                el_path = ElementPath(el_path)
            # Make sure correct root path
            if not (el_path.star or el_path.non_fhir):
                self._validate_root_path(str(el_path))
            self._select.append(el_path)

    @builder
    def exclude(self, *args):
        """ """
        self._pre_check()

        for el_path in args:
            if not IElementPath.providedBy(el_path):
                el_path = ElementPath(el_path)
            # Make sure correct root path
            if not (el_path.star or el_path.non_fhir):
                self._validate_root_path(str(el_path))
            self._exclude.append(el_path)

    @builder
    def where(self, *args, **kwargs):
        """ """
        self._pre_check()

        if len(kwargs) > 0:
            for path, value in kwargs.items():
                term = and_(path, value)

                self._validate_term_path(term)
                self._where.append(term)

        for term in args:
            assert ITerm.providedBy(term) is True

            self._validate_term_path(term)
            self._where.append(term)

    @builder
    def limit(self, limit: int, offset: int = 0):
        """ """
        self._pre_check()
        self._limit.limit = limit
        self._limit.offset = offset

    @builder
    def sort(self, *args):
        """ """
        self._pre_check()

        for sort_path in args:
            if not ISortTerm.providedBy(sort_path):
                if isinstance(sort_path, (tuple, list)):
                    sort_path = sort_(*sort_path)
                else:
                    sort_path = sort_(sort_path)
            self._sort.append(sort_path)

    def get_query(self) -> "Query":
        """ """
        required_finalized(self)

        return Query.from_builder(self)

    def __fql__(self):
        """ """
        required_finalized(self)

        return fql(self.context.dialect.bind(self))

    def __str__(self):
        """ """
        required_finalized(self)

        return self.__fql__()

    def __call__(
        self,
        unrestricted: bool = False,
        engine: Optional["Engine"] = None,
        async_result: bool = False,
    ) -> Union["QueryResult", "AsyncQueryResult"]:
        """ """
        if not self._finalized and (engine or self._engine):
            self.finalize(engine)

        query = self.get_query()
        result_factory = QueryResult
        if async_result is True:
            result_factory = AsyncQueryResult
        if TYPE_CHECKING:
            assert self._engine
        result = result_factory(query=query, engine=self._engine, unrestricted=unrestricted)
        return result

    def _pre_check(self):
        """ """
        # TODO can we modify this check somehow?
        # required_from_resource(self)
        required_not_finalized(self)

    def _validate(self):
        """ """
        # validate select elements
        if any([el.star for el in self._select]) and len(self._select) > 1:
            raise ValidationError("select(*) cannot co-exists other select element!")

    def _validate_root_path(self, path_string: str):
        """ """
        root_path = path_string.split(".")[0]

        if self._from:
            match = any(alias == root_path for alias, _ in self._from)
        else:
            # FIXME ugly
            match = root_path == "Resource"

        if not match:
            raise ValidationError(
                "Root path '{0!s}' must be matched with from models".format(root_path)
            )

    def _validate_term_path(self, term):
        """ """
        if IGroupTerm.providedBy(term):
            for trm in term.terms:
                self._validate_term_path(trm)
        else:
            self._validate_root_path(str(term.path))


@implementer(IQueryResult)
class QueryResult(ABC):
    """ """

    def __init__(self, query: Query, engine: "Engine", unrestricted: bool = False):
        """ """
        self._query: Query = query
        self._engine: "Engine" = engine
        self._unrestricted: bool = unrestricted

    def fetchall(self):
        """ """
        result = self._engine.execute(self._query, self._unrestricted)
        return result

    def single(self):
        """Will return the single item in the input if there is just one item.
        If the input collection is empty ({ }), the result is empty.
        If there are multiple items, an error is signaled to the evaluation environment.
        This operation is useful for ensuring that an error is returned
        if an assumption about cardinality is violated at run-time."""
        result = self.fetchall()
        if result.header.total == 0:
            return None
        if result.header.total > 1:
            raise MultipleResultsFound

        return result.body[0]

    def first(self):
        """Returns a collection containing only the first item in the input collection.
        This function is equivalent to item(0), so it will return an empty collection
        if the input collection has no items."""
        query = self._query.clone()
        query._limit.limit = 1
        result = self._engine.execute(query, self._unrestricted)
        if result.header.total > 0:
            return result.body[0]
        return None

    def last(self):
        """Returns a collection containing only the last item in the input collection.
        Will return an empty collection if the input collection has no items."""

    def tail(self):
        """Returns a collection containing all but the first item in the input
        collection. Will return an empty collection
        if the input collection has no items, or only one item."""

    def skip(self, num: int):
        """Returns a collection containing all but the first num items
        in the input collection. Will return an empty collection
        if there are no items remaining after the indicated number of items have
        been skipped, or if the input collection is empty.
        If num is less than or equal to zero, the input collection
        is simply returned."""

    def take(self, num: int):
        """Returns a collection containing the first num items in the input collection,
        or less if there are less than num items. If num is less than or equal to 0, or
        if the input collection is empty ({ }), take returns an empty collection."""

    def count(self):
        """Returns a collection with a single value which is the integer count of
        the number of items in the input collection.
        Returns 0 when the input collection is empty."""
        result = self._engine.execute(self._query, self._unrestricted, EngineQueryType.COUNT)
        # return result.header.total
        return result

    def empty(self):
        """Returns true if the input collection is empty ({ }) and false otherwise."""
        return self.count() == 0

    def __len__(self):
        """ """
        return self.count()

    def OFF__getitem__(self, key):
        """
        Lazy loading es results with negative index support.
        We store the results in buckets of what the bulk size is.
        This is so you can skip around in the indexes without needing
        to load all the data.
        Example(all zero based indexing here remember)::

            (525 results with bulk size 50)
            - self[0]: 0 bucket, 0 item
            - self[10]: 0 bucket, 10 item
            - self[50]: 50 bucket: 0 item
            - self[55]: 50 bucket: 5 item
            - self[352]: 350 bucket: 2 item
            - self[-1]: 500 bucket: 24 item
            - self[-2]: 500 bucket: 23 item
            - self[-55]: 450 bucket: 19 item
        """
        # if isinstance(key, slice):
        #     return [self[i] for i in range(key.start, key.end)]
        # else:
        #     if key + 1 > self.count:
        #         raise IndexError
        #     elif key < 0 and abs(key) > self.count:
        #         raise IndexError

        #     if key >= 0:
        #         result_key = (key / self.bulk_size) * self.bulk_size
        #         start = result_key
        #         result_index = key % self.bulk_size
        #     elif key < 0:
        #         last_key = (
        #             int(math.floor(float(self.count) / float(self.bulk_size)))
        #             * self.bulk_size
        #         )
        #         start = result_key = last_key - (
        #             (abs(key) / self.bulk_size) * self.bulk_size
        #         )
        #         if last_key == result_key:
        #             result_index = key
        #         else:
        #             result_index = (key % self.bulk_size) - (
        #                 self.bulk_size - (self.count % last_key)
        #             )

        #     if result_key not in self.results:
        #         self.results[result_key] = self.es._search(
        #             self.query, sort=self.sort, start=start, **self.query_params
        #         )["hits"]["hits"]

        #     return self.results[result_key][result_index]

    def __iter__(self):
        """ """
        result = self._engine.execute(self._query, self._unrestricted)
        model_class = self._query.get_from()[0][1]
        for row in result.body:
            if self._query.get_select()[0].star:
                yield model_class(**row[0])
            else:
                yield row


class AsyncQueryResult(QueryResult):
    """ """

    async def fetchall(self):
        """ """
        result = await self._engine.execute(self._query, self._unrestricted)
        return result

    async def __aiter__(self):
        """ """
        result = await self._engine.execute(self._query, self._unrestricted)
        model_class = self._query.get_from()[0][1]
        for row in result.body:
            if self._query.get_select()[0].star:
                yield model_class(**row[0])
            else:
                yield row

    async def single(self):
        """ """
        result = await self.fetchall()
        if result.header.total == 0:
            return None
        if result.header.total > 1:
            raise MultipleResultsFound
        return result.body[0]

    async def first(self):
        """ """
        query = self._query.clone()
        query._limit.limit = 1
        result = await self._engine.execute(query, self._unrestricted)
        if result.header.total > 0:
            return result.body[0]
        return None

    async def count(self):
        """ """
        result = await self._engine.execute(self._query, self._unrestricted, EngineQueryType.COUNT)
        return result.header.total

    async def empty(self):
        """Returns true if the input collection is empty ({ }) and false otherwise."""
        return await self.count() == 0

    def __len__(self):
        """ """
        return self.count()


def Q_(resource_names=None, engine=None):
    """ """
    builder = Query._builder(engine)
    if resource_names:
        builder = builder.from_(resource_names)
    return builder
