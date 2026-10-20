"""Observe one host pause signal without owning any model or workflow state."""
import threading
from .cow_client import OperationIndeterminate,RequestRejected


class PauseWatcher:
    def __init__(self,operation,control,pause,notice,*,interval=.1):
        if control is not None and not callable(control):raise ValueError('Read-only model pause callback required')
        self.operation=operation;self.control=control;self.pause=pause;self.notice=notice
        self.interval=interval;self.done=threading.Event();self.requested=False;self.thread=None

    def __enter__(self):
        if self.control is not None:
            self.thread=threading.Thread(target=self._watch,name='branchwrite-model-pause',daemon=False)
            self.thread.start()
        return self

    def _notify(self,message):
        try:self.notice(message)
        except Exception:pass  # Presentation cannot change the original call's settlement.

    def _watch(self):
        failures=0
        while not self.done.wait(self.interval):
            try:
                requested=self.control()
                if type(requested) is not bool:raise ValueError('Model pause observer must return a boolean')
                if not requested:continue
                reply=self.pause(self.operation)
                if reply['pause_requested']:
                    self.requested=True
                    self._notify('Pause requested; waiting for the original saved model result.')
                    return
                # HTTP registration may lag admission. Poll the same control,
                # never generation, until the original call completes.
                failures=0
            except RequestRejected:
                self._notify('Server pause is unavailable; waiting for the current model step.')
                return
            except OperationIndeterminate:
                # Event.set on this exact operation is idempotent. A lost
                # control reply is not permission to resend model generation.
                failures+=1
                if failures<3:continue
                self._notify('Pause control could not be confirmed; waiting for the current model step.')
                return
            except Exception:
                self._notify('Pause observer failed; waiting for the current model step.')
                return

    def __exit__(self,*args):
        self.done.set()
        if self.thread is not None:self.thread.join()
