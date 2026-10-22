"""Real thread overlap; workers never receive the workflow kernel."""
import threading
import unittest
from branchwrite.parallel_dispatch import DispatchPool


class DispatchTests(unittest.TestCase):
    def test_two_slots_overlap_and_a_third_waits(self):
        pool = DispatchPool(2)
        self.addCleanup(pool.close)
        entered = [threading.Event(), threading.Event()]
        release = threading.Event()
        self.addCleanup(release.set)
        def work(index):
            entered[index].set()
            if not release.wait(3):raise TimeoutError('test gate')
            return index
        self.assertTrue(pool.submit('first', lambda: work(0)))
        self.assertTrue(pool.submit('second', lambda: work(1)))
        self.assertTrue(all(event.wait(1) for event in entered))
        self.assertFalse(pool.submit('third', lambda: None))
        self.assertFalse(pool.ready('first'))
        release.set()
        pool.wait(.1)
        self.assertEqual(pool.take('first'), 0)
        self.assertEqual(pool.take('second'), 1)
        self.assertFalse(pool.pending)

    def test_duplicate_id_and_stopped_admission_cannot_dispatch_again(self):
        with DispatchPool(1) as pool:
            self.assertTrue(pool.submit('one', lambda: 1))
            with self.assertRaises(ValueError):pool.submit('one', lambda: 2)
            pool.admitting = False
            self.assertFalse(pool.submit('two', lambda: 2))
            pool.wait(.1)
            self.assertEqual(pool.take('one'), 1)

    def test_wrong_thread_cannot_mutate_dispatch_ownership(self):
        with DispatchPool(1) as pool:
            errors = []
            def other():
                try:pool.submit('foreign', lambda: None)
                except RuntimeError as error:errors.append(str(error))
            t = threading.Thread(target=other);t.start();t.join()
            self.assertEqual(len(errors), 1)

    def test_drain_collects_other_receipts_even_if_one_collection_fails(self):
        with DispatchPool(2) as pool:
            observed=[];owner=threading.get_ident()
            def collect_bad():
                pool.take('bad')
                raise ValueError('unknown malformed receipt')
            def collect_good():
                observed.append((pool.take('good'),threading.get_ident()))
            pool.submit('bad',lambda:1,collect=collect_bad)
            pool.submit('good',lambda:2,collect=collect_good)
            with self.assertRaisesRegex(ValueError,'malformed receipt'):pool.drain()
            self.assertEqual(observed,[(2,owner)])
            self.assertFalse(pool.pending)
            self.assertFalse(pool.submit('third',lambda:3))

    def test_frozen_slot_count_cannot_change_after_admission(self):
        with DispatchPool(1) as pool:
            with self.assertRaises(AttributeError):pool.slots=2


if __name__ == '__main__':unittest.main()
