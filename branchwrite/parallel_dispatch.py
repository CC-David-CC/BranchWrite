"""Bounded host effects. Only the interpreter owner admits and collects work.

Futures are transient execution handles, never a recovery ledger. After restart
the original Kernel dispatch and COW/Executor receipts remain authoritative.
"""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import threading


class DispatchPool:
    def __init__(self, slots):
        if type(slots) is not int or not 1 <= slots <= 8:
            raise ValueError('Parallel dispatch requires 1..8 host slots')
        self._slots = slots
        self.admitting = True
        self._owner = threading.get_ident()
        self._futures = {}
        self._collectors = {}
        self._executor = ThreadPoolExecutor(max_workers=slots, thread_name_prefix='bw-effect')

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Only the workflow owner may control dispatch')

    @property
    def slots(self):return self._slots

    @property
    def pending(self):
        self._check()
        return bool(self._futures)

    @property
    def available(self):
        self._check()
        return self.admitting and sum(not f.done() for f in self._futures.values()) < self.slots

    def contains(self, operation):
        self._check()
        return operation in self._futures

    def submit(self, operation, call, *, collect=None):
        self._check()
        if operation in self._futures:
            raise ValueError('Operation already has a live dispatch handle')
        if not self.available:return False
        self._futures[operation] = self._executor.submit(call)
        if collect is not None:self._collectors[operation] = collect
        return True

    def ready(self, operation):
        self._check()
        return self._futures[operation].done()

    def take(self, operation):
        self._check()
        future = self._futures[operation]
        if not future.done():raise RuntimeError('Cannot collect unfinished work')
        del self._futures[operation]
        self._collectors.pop(operation,None)
        return future.result()

    def drain(self):
        """Retire dispatched effects on the owner before closing its ledger.

        This admits no new effects. If collection fails, the original durable
        dispatch stays unresolved; another candidate's known result is still
        collected. Unknown effects never become fresh dispatches.
        """
        self._check()
        self.admitting = False
        errors=[]
        while self._collectors:
            self.wait(.05)
            for operation in tuple(self._collectors):
                if not self.ready(operation):continue
                collector=self._collectors[operation]
                try:collector()
                except BaseException as error:
                    errors.append(error)
                    # Do not let a malformed receipt strand other known work.
                    self._collectors.pop(operation,None)
                    self._futures.pop(operation,None)
        if errors:raise errors[0]

    def wait(self, seconds=.05):
        self._check()
        futures = [f for f in self._futures.values() if not f.done()]
        if futures:wait(futures, timeout=seconds, return_when=FIRST_COMPLETED)

    def close(self):
        self._check()
        self.admitting = False
        self._executor.shutdown(wait=True, cancel_futures=False)

    def __enter__(self):return self
    def __exit__(self, *args):self.close()
