"""Fallback updater used by React base classes."""


class ReactNoopUpdateQueue:
    def enqueueSetState(self, public_instance, partial_state, callback=None, callerName=None):
        return None

    def enqueueForceUpdate(self, public_instance, callback=None, callerName=None):
        return None


updater = ReactNoopUpdateQueue()

