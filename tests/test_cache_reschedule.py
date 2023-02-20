import datetime
from uuid import uuid4

from toodledo import Task


def test_cache_reschedule(cache):
    comp = cache.comp
    account = cache.toodledo.GetAccount()
    cache.update()
    before_add_size = len(cache)
    new_task = cache.AddTasks([Task(title=str(uuid4()), repeat='DAILY')])[0]
    edited_task = cache.EditTasks([Task(
        id_=new_task.id_,
        completedDate=datetime.date.today(),
        reschedule=1)])[0]
    after_add_size = len(cache)
    assert edited_task.completedDate is None
    assert edited_task.id_ == new_task.id_
    assert edited_task.title == new_task.title
    if comp is None:
        assert after_add_size == before_add_size + 2
    elif comp == 0:
        assert after_add_size == before_add_size + 1
    elif comp == 1:
        # Because the cache only has completed tasks in it, the task we
        # initially added above wasn't saved in the cache after it was added,
        # which means that the newly created completed task also wasn't saved
        # in the cache after the edit, which is expected behavior.
        assert after_add_size == before_add_size

    created = [t
               for t in cache.toodledo.GetTasks(
                       params={'after': account.lastEditTask})
               if t.title == new_task.title]
    cache.DeleteTasks(created)
    after_delete_size = len(cache)
    assert after_delete_size == before_add_size
