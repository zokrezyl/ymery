from ymery.result import Result, Ok
from ymery.types import Object


class Dispatcher(Object):
    """
    The dispatcher has double role:
    to dispatch actions and events
    Difference between action and event:
    -> an event listener may react to an event, but there must not necessary exist an object that reacts
    -> for an action there must be at least one responder
    -> if multiple responders (handlers) registered, each must return success
    the action dispatcher connects action requester with action handler
    """
    def __init__(self):
        self._action_handlers = {}  # target-id -> handler
        self._event_handlers = {}  # source or source/name -> list of handlers

    # ========== Action Handler Methods ==========

    def register_action_handler(self, handler) -> Result[None]:
        """Register an action handler

        Args:
            handler: Handler object implementing handle_action() method (must have uid attribute)
        """
        self._action_handlers[handler.uid] = handler
        return Ok(None)

    def unregister_action_handler(self, handler_id: str) -> Result[None]:
        """Unregister an action handler

        Args:
            handler_id: ID of the handler to unregister
        """
        if handler_id in self._action_handlers:
            del self._action_handlers[handler_id]
        return Ok(None)

    # ========== Event Handler Methods ==========

    def register_event_handler(self, key: str, handler) -> Result[None]:
        """Register an event handler for source or source/name

        Args:
            key: Either "source" or "source/name" (e.g., "asset-tree" or "asset-tree/tree-node-clicked")
            handler: Handler object implementing handle_event() method
        """
        if key not in self._event_handlers:
            self._event_handlers[key] = []
        if handler not in self._event_handlers[key]:
            self._event_handlers[key].append(handler)

        return Ok(None)

    def unregister_event_handler(self, key: str, handler) -> Result[None]:
        """Unregister an event handler

        Args:
            key: The source or source/name key
            handler: Handler to unregister
        """
        if key in self._event_handlers:
            if handler in self._event_handlers[key]:
                self._event_handlers[key].remove(handler)
            if not self._event_handlers[key]:
                del self._event_handlers[key]
        return Ok(None)

    # ========== Dispatch Methods ==========

    def dispatch_action(self, action: dict):
        """Dispatch action to the target handler

        action dict:
        "action": mandatory - action name
        "target-id": mandatory - target handler ID
        "data": optional - additional data

        Returns:
            Result from handler (True for success, Error/False for failure, or None)
        """
        action_name = action.get("action")
        target_id = action.get("target-id")

        # Target handler is mandatory for actions
        if target_id and target_id in self._action_handlers:
            result = self._action_handlers[target_id].handle_action(action)
            return result

        return None

    def dispatch_event(self, event: dict) -> Result[None]:
        """Dispatch event to registered handlers (fire-and-forget)

        event dict:
        "source": source id (mandatory)
        "name": event name (mandatory)
        "data": additional data (optional)

        Events are routed to handlers registered for:
        1. "source/name" (specific event from specific source)
        2. "source" (all events from this source)
        """
        source = event.get("source")
        name = event.get("name")

        if not source or not name:
            return Ok(None)


        # Route to specific source/name handlers
        key_specific = f"{source}/{name}"
        if key_specific in self._event_handlers:
            for handler in self._event_handlers[key_specific]:
                res = handler.handle_event(event)
                if not res:
                    return Result.error("event handler error", res)
        # Route to source-wide handlers
        if source in self._event_handlers:
            for handler in self._event_handlers[source]:
                res = handler.handle_event(event)
                if not res:
                    return Result.error("event handler handling not successfull", res)

        return Ok(None)


    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)

