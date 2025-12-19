import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar, Union
from typing import Any

def as_tree(obj: Any) -> dict | list:
    """
    Convert an object to a tree structure.
    """
    if hasattr(obj, "as_tree"):
        return obj.as_tree

    match obj:
        case dict() :
            new_dict = {}
            for key, value in obj.items():
                new_dict[key] = as_tree(value)
            return new_dict
        case list() :
            new_list = []
            for value in obj:
                new_list.append(as_tree(value))
            return new_list
        case tuple() : 
            return str(obj)
        case set() : 
            return obj
        case int() | float() | str() | bool():
            return obj
        case _:
            return str(obj)


""" Generic Rust like Result[T] pattern implementation"""


_CONSRUCTOR_TOKEN = "Error class constructor should not be called directly. Use Error.create() instead."


def _adapt_error(value: Optional[Union[str, dict, list, Exception, "Error", "Err"]]) -> Optional[Union[str, dict, list, "Error"]]:
    """Factory method to create Error from any supported type"""
    if value is None:
        return None
    match value:
        case Error():
            return value
        case str():
            return value
        case dict():
            return value
        case list():
            # Check if list contains error types (Error, Err, Exception, str, dict)
            if len(value) > 0 and any(isinstance(item, (Error, Err, Exception, str, dict)) for item in value):
                # Adapt each error in the list
                return [_adapt_error(item) for item in value]
            return value
        case Exception():
            # Extract relevant information from the exception
            stack = traceback.format_tb(value.__traceback__) if value.__traceback__ else None
            if False:
                return {
                    "type": type(value).__name__,
                    "message": str(value),
                    "args": value.args if value.args else None,
                    "module": getattr(type(value), "__module__", None),
                    "stack": stack
                }
            return "exception"
        case Err():
            return value._error
        case _:
            return {
                "message": "unknown type provided for Error constructor",
                "type": type(value).__name__, "value": str(value)}

class Error:
    """ Inner representation of an error"""
    def __init__(self, _constructor_token: str, error: Union[str, dict, list, Exception, "Error", "Err"], prev_error: Optional[Union[str, dict, list, Exception, "Error", "Err"]] = None):
        self._error = error
        self._prev_error = prev_error
        # Capture the call stack, excluding this constructor frame
        self._stack = traceback.extract_stack()[:-1] 

    @property
    def error(self):
        return self._error

    @property
    def __as_tree(self) -> dict:
        """Convert the error to a dictionary representation."""
        error = None
        match self._error:
            case str() | dict() | list():
                error = self._error
            case Error():
                error = self._error.as_tree
            case _:
                error = str(self._error)
        prev_error = None
        match self._prev_error:
            case None:
                prev_error = None
            case str() | dict() | list():
                prev_error = self._prev_error
            case Error():
                prev_error = self._prev_error.as_tree
            case _:
                prev_error = str(self._prev_error)
        tree = {}
        if error:
            tree["error"] = error
        if prev_error:
            tree["prev_error"] = prev_error
        return tree

    @property
    def as_tree(self) -> dict:
        """Convert the error to a tree structure."""
        return {
            "error": as_tree(self._error),
            "prev_error": as_tree(self._prev_error),
        }

    @property
    def prev_error(self):
        return self._prev_error

    @property
    def stack(self):
        return self._stack

    def __repr__(self):
        return f"Error({self._error!r}, prev_error={self._prev_error!r})"

    def __str__(self):
        return f"Error: {self._error}, Previous: {self._prev_error}, Stack: {self._stack}"

    @classmethod
    def create(cls, value: Union[str, dict, list, Exception, "Error", "Err"], prev_error: Optional[Union[str, dict, list, Exception, "Error", "Err"]] = None) -> "Error":
        """Create an Error instance with the given value and optional previous error."""
        return cls(_CONSRUCTOR_TOKEN, _adapt_error(value), _adapt_error(prev_error))


class NoneValueError(Error):
    """Indicates that an expected value was None."""

    def __init__(self, message: str = "Unexpected None"):
        super().__init__(_CONSRUCTOR_TOKEN, message)


T = TypeVar("T")
U = TypeVar("U")


class Result(Generic[T]):
    """Base class for Ok and Err
    """
    def __bool__(self) -> bool:
        return self.is_ok

    @property
    @abstractmethod
    def value(self) -> T:
        """Get the value of a Result instance
        Use this property with caution. For non Err case, use explicitelly unwrapped instead, to make the code more readable
        'res.value' may be practical when for debugging, logging etc purposes one just wants to see the result of a call, wether successful or not.

        """


    @property
    @abstractmethod
    def is_ok(self) -> bool:
        """ Check if this Result is Ok.

        Returns True if this Result is Ok, False if it is Err.
        """

    @property
    @abstractmethod
    def is_err(self) -> bool:
        """ Check if this Result is any kind of Err implementation.
        Returns True if this Result is Err, False if it is Ok.
        """

    @property
    @abstractmethod
    def unwrapped(self) -> T:
        """Alias for unwrap, for consistency with Rust's Result."""

    @classmethod
    def error(
        cls,
        err: Union[Error, str, list, dict, Exception],
        prev_error: Optional[Union["Result", Error, "Err", Exception]] = None,
    ) -> "Result[T]":
        """Helper method to create an Err result
        Using Result.error() makes the code more readable as it suggest that this is an error case in the context of Result pattern
        Usage:
            Result.error("An error occurred")
            res = my_object.do_something()
            if not res:
                Result.error("An error occurred")
            try:
                value = call_external_api()
            except SomeeException as e:
                Result.error("Exception occurred while ....", e)

        """
        return Err.create(err, prev_error)

    # ===== FLUENT API METHODS (inspired by Rust Result) =====

    def and_then(self, func: Callable[[T], "Result[U]"]) -> "Result[U]":
        """Chain operations that return Results - like flatMap.

        If this Result is Ok(value), calls func(value) and returns its Result.
        If this Result is Err, returns the Err unchanged.
        """
        if self.is_ok:
            return func(self.unwrapped)
        else:
            return Err(self._error)  # type: ignore

    def or_else(self, func: Callable[[dict], "Result[T]"]) -> "Result[T]":
        """Handle errors by providing alternative Results.

        If this Result is Err(error), calls func(error) and returns its Result.
        If this Result is Ok, returns the Ok unchanged.
        """
        if self.is_err:
            return func(self._error.error)  # type: ignore
        else:
            return self

    def map(self, func: Callable[[T], U]) -> "Result[U]":
        """Transform Ok values, pass through Err unchanged.

        If this Result is Ok(value), returns Ok(func(value)).
        If this Result is Err, returns the Err unchanged.
        """
        if self.is_ok:
            return Ok(func(self.unwrapped))
        else:
            return Err(self._error)  # type: ignore

    def map_err(self, func: Callable[[dict], dict]) -> "Result[T]":
        """Transform Err values, pass through Ok unchanged.

        If this Result is Err(error), returns Err(func(error)).
        If this Result is Ok, returns the Ok unchanged.
        """
        if self.is_err:
            return Err(func(self._error.error))  # type: ignore
        else:
            return self

    def unwrap_or(self, default: T) -> T:
        """Return value or default if Err.

        If this Result is Ok(value), returns value.
        If this Result is Err, returns default.
        """
        return self.unwrapped if self.is_ok else default

    def unwrap_or_else(self, func: Callable[[dict], T]) -> T:
        """Return value or call function with error.

        If this Result is Ok(value), returns value.
        If this Result is Err(error), returns func(error).
        """
        return self.unwrapped if self.is_ok else func(self._error.error)  # type: ignore

    def inspect(self, func: Callable[[T], None]) -> "Result[T]":
        """Call function with Ok value for side effects, return self unchanged.

        Useful for debugging or logging without changing the Result.
        """
        if self.is_ok:
            func(self.unwrapped)
        return self

    def inspect_err(self, func: Callable[[dict], None]) -> "Result[T]":
        """Call function with Err value for side effects, return self unchanged.

        Useful for debugging or logging errors without changing the Result.
        """
        if self.is_err:
            func(self._error.error)  # type: ignore
        return self


@dataclass(frozen=True)
class Ok(Result[T]):
    _value: T

    @property
    def is_ok(self) -> bool:
        """Check if this Result is Ok."""
        return True
    
    @property
    def is_err(self) -> bool:
        """Check if this Result is Err."""
        return False

    @property
    def value(self) -> T:
        """Get the value of this Ok result."""
        return self._value

    @property
    def as_tree(self) -> dict:
        return {"value": as_tree(self._value)}

    @property
    def unwrapped(self) -> T:
        """Alias for unwrap, for consistency with Rust's Result."""
        return self._value


@dataclass(frozen=True)
class Err(Result[T]):
    _error: Error

    @property
    def is_ok(self) -> bool:
        """Check if this Result is Ok."""
        return False
    
    @property
    def is_err(self) -> bool:
        """Check if this Result is Err."""
        return True

    def __post_init__(self):
        # Convert raw error types to Error objects
        if not isinstance(self._error, Error):
            object.__setattr__(self, '_error', Error.create(self._error))

    @property
    def error(self) -> Error:
        return self._error

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    @property
    def as_tree(self) -> dict:
        return {"error": self._error.as_tree}

    @classmethod
    def create(
        cls,
        error: Union[Error, str, dict, list, Exception],
        prev_error: Optional[Union[Error, str, dict, list, Exception, "Err"]] = None,
    ) -> "Err[T]":
        """Create an Err result with chained error tree structure"""
        return cls(_error=Error.create(error, prev_error))

    @property
    def unwrapped(self) -> T:
        return Err.create("Cannot unwrap an Err Result", self)


    @property
    def value(self) -> T:
        """Get the value of this Err result.
        """
        return self._error


def non_none_result(
    value: Optional[T], err: str = "unexpected None value"
) -> Result[T]:
    if value is None:
        return Result.error(err)
    return Ok(value)
