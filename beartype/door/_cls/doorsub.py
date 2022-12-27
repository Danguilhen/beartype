#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright (c) 2014-2022 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype Decidedly Object-Oriented Runtime-checking (DOOR) middle-men
subclasses** (i.e., abstract subclasses of the object-oriented type hint class
hierarchy simplifying the definition of concrete subclasses of this hierarchy).

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ IMPORTS                            }....................
from abc import abstractmethod
from beartype.door._cls.doorsuper import TypeHint
from beartype.roar import BeartypeDoorException
from beartype.typing import (
    Any,
)
from beartype._util.cache.utilcachecall import (
    property_cached,
)

# ....................{ SUBCLASSES                         }....................
class _TypeHintSubscripted(TypeHint):
    '''
    **Subscripted type hint wrapper** (i.e., high-level object encapsulating a
    low-level parent type hint subscripted (indexed) by one or more equally
    low-level children type hints).
    '''

    # ..................{ PRIVATE ~ properties : concrete    }..................
    @property  # type: ignore[misc]
    @property_cached
    def _is_args_ignorable(self) -> bool:
        '''
        ``True`` only if all child type hints subscripting (indexing) this
        parent type hint are ignorable.

        Note that this property is *not* equivalent to the :meth:`is_ignorable`
        property. Although related, a non-ignorable parent type hint can
        trivially have ignorable child type hints (e.g., ``list[Any]``).
        '''

        #FIXME: Kinda unsure about this. Above, we define "_origin" as:
        #   self._origin: type = get_hint_pep_origin_or_none(hint) or hint  # type: ignore
        #
        #That effectively reduces to:
        #   self._origin: type = hint.__origin__ or hint  # type: ignore
        #FIXME: Ideally, this should read:
        #    return all(
        #        hint_child.is_ignorable
        #        for hint_child in self._args_wrapped_tuple
        #    )
        #
        #Sadly, that refactoring currently raises non-trivial test failures.
        #Let's investigate at a later time, please.
        return all(
            hint_child._origin is Any
            for hint_child in self._args_wrapped_tuple
        )

    # ..................{ PRIVATE ~ testers                  }..................
    def _is_le_branch(self, branch: TypeHint) -> bool:

        # If the other branch was *NOT* subscripted, we assume it was
        # subscripted by "Any" and simply check that the origins are compatible.
        if branch._is_args_ignorable:
            return issubclass(self._origin, branch._origin)
        # Else, the other branch was subscripted.

        return (
            # That branch is also a type hint wrapper of the same concrete
            # subclass as this type hint wrapper *AND*...
            isinstance(branch, type(self)) and
            # The low-level unordered type hint encapsulated by this
            # high-level partially ordered type hint is a subclass of
            # The low-level unordered type hint encapsulated by the branch
            issubclass(self._origin, branch._origin) and
            # *AND* All child (argument) hints are subclasses of the
            # corresponding branch child hint
            all(
                self_child <= branch_child
                for self_child, branch_child in zip(
                    self._args_wrapped_tuple, branch._args_wrapped_tuple
                )
            )
        )

# ....................{ SUBCLASSES ~ isinstanceable        }....................
class _TypeHintOriginIsinstanceable(_TypeHintSubscripted):
    '''
    **Isinstanceable type hint wrapper** (i.e., high-level object
    encapsulating a low-level parent type hint subscripted (indexed) by exactly
    one or more low-level child type hints originating from isinstanceable
    classes such that *all* objects satisfying those hints are instances of
    those class).
    '''

    # ..................{ PRIVATE ~ properties               }..................
    @property
    @abstractmethod
    def _args_len_expected(self) -> int:
        '''
        Number of child type hints that this instance of a concrete subclass of
        this abstract base class (ABC) is expected to be subscripted (indexed)
        by.
        '''

        pass

    # ..................{ PRIVATE ~ factories                }..................
    def _make_args(self) -> tuple:

        # Tuple of the zero or more low-level child type hints subscripting
        # (indexing) the low-level parent type hint wrapped by this wrapper.
        args = super()._make_args()

        # If this hint was subscripted by an unexpected number of child hints...
        if len(args) != self._args_len_expected:
            #FIXME: This seems sensible, but currently provokes test failures.
            #Let's investigate further at a later time, please.
            # # If this hint was subscripted by *NO* parameters, comply with PEP
            # # 484 standards by silently pretending this hint was subscripted by
            # # the "typing.Any" fallback for all missing parameters.
            # if len(self._args) == 0:
            #     return (Any,)*self._args_len_expected

            #FIXME: Consider raising a less ambiguous exception type, yo.
            #FIXME: Consider actually testing this. This *IS* technically
            #testable and should thus *NOT* be marked as "pragma: no cover".

            # In most cases it will be hard to reach this exception, since most
            # of the typing library's subscripted type hints will raise an
            # exception if constructed improperly.
            raise BeartypeDoorException(  # pragma: no cover
                f'{type(self)} type must have {self._args_len_expected} '
                f'argument(s), but got {len(args)}.'
            )
        # Else, this hint was subscripted by the expected number of child hints.

        # Return these child hints.
        return args

    # ..................{ PRIVATE ~ testers                  }..................
    # Note that this redefinition of the superclass _is_equal() method is
    # technically unnecessary, as that method is already sufficiently
    # general-purpose to suffice for *ALL* possible subclasses (including this
    # subclass). Nonetheless, we wrote this method first. More importantly, this
    # method is *SUBSTANTIALLY* faster than the superclass method. Although
    # efficiency is typically *NOT* a pressing concern for the DOOR API,
    # discarding faster working code would be senseless.
    def _is_equal(self, other: TypeHint) -> bool:

        # If *ALL* of the child type hints subscripting both of these parent
        # type hints are ignorable, return true only if these parent type hints
        # both originate from the same isinstanceable class.
        if self._is_args_ignorable and other._is_args_ignorable:
            return self._origin == other._origin
        # Else, one or more of the child type hints subscripting either of these
        # parent type hints are unignorable.
        #
        # If either...
        elif (
            # These hints have differing signs *OR*...
            self._hint_sign is not other._hint_sign or
            # These hints have a differing number of child type hints...
            len(self._args_wrapped_tuple) != len(other._args_wrapped_tuple)
        ):
            # Then these hints are unequal.
            return False
        # Else, these hints share the same sign and number of child type hints.

        # Return true only if all child type hints of these hints are equal.
        return all(
            this_child == that_child
            #FIXME: Probably more efficient and maintainable to write this as:
            #    for this_child in self
            #    for that_child in other
            for this_child, that_child in zip(
                self._args_wrapped_tuple, other._args_wrapped_tuple)
        )


class _TypeHintOriginIsinstanceableArgs1(_TypeHintOriginIsinstanceable):
    '''
    **1-argument isinstanceable type hint wrapper** (i.e., high-level object
    encapsulating a low-level parent type hint subscripted (indexed) by exactly
    one low-level child type hint originating from an isinstanceable class such
    that *all* objects satisfying that hint are instances of that class).
    '''

    @property
    def _args_len_expected(self) -> int:
        return 1


class _TypeHintOriginIsinstanceableArgs2(_TypeHintOriginIsinstanceable):
    '''
    **2-argument isinstanceable type hint wrapper** (i.e., high-level object
    encapsulating a low-level parent type hint subscripted (indexed) by exactly
    two low-level child type hints originating from isinstanceable classes such
    that *all* objects satisfying those hints are instances of those classes).
    '''

    @property
    def _args_len_expected(self) -> int:
        return 2


class _TypeHintOriginIsinstanceableArgs3(_TypeHintOriginIsinstanceable):
    '''
    **3-argument isinstanceable type hint wrapper** (i.e., high-level object
    encapsulating a low-level parent type hint subscripted (indexed) by exactly
    three low-level child type hints originating from isinstanceable classes
    such that *all* objects satisfying those hints are instances of those
    classes).
    '''

    @property
    def _args_len_expected(self) -> int:
        return 3
