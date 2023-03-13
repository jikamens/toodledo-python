import datetime
from uuid import uuid4

import pytest

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
    assert edited_task.completedDate is None
    assert edited_task.id_ == new_task.id_
    assert edited_task.title == new_task.title
    tasks = [t for t in cache.GetTasks(comp=comp, fields='duedate')
             if t.title == new_task.title]
    # Assumes ids go in in increasing order by when they're created
    tasks.sort(key=lambda t: t.id_)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    if comp is None:
        assert len(tasks) == 2
        assert tasks[0].id_ == new_task.id_
        assert tasks[0].dueDate == tomorrow
    elif comp == 0:
        assert len(tasks) == 1
        assert tasks[0].id_ == new_task.id_
        assert tasks[0].dueDate == tomorrow
    elif comp == 1:
        assert len(tasks) == 1
        assert tasks[0].id_ != new_task.id_

    created = [t
               for t in cache.toodledo.GetTasks(after=account.lastEditTask)
               if t.title == new_task.title]
    cache.DeleteTasks(created)
    after_delete_size = len(cache)
    assert after_delete_size == before_add_size


@pytest.mark.parametrize("complete_task", [False, True])
def test_cache_preserve_tasks(cache, complete_task):
    """Test that the tasks which should remain in the cache do."""
    incomplete_in_cache = cache.comp is None or cache.comp == 0
    complete_in_cache = cache.comp is None or cache.comp == 1
    before_add_size = len(cache)
    added_task = cache.AddTasks([Task(title=str(uuid4()))])[0]
    after_add_size = len(cache)
    if incomplete_in_cache:
        assert after_add_size == before_add_size + 1
        next(t for t in cache if t.id_ == added_task.id_)
    else:
        assert after_add_size == before_add_size
        with pytest.raises(StopIteration):
            next(t for t in cache if t.id_ == added_task.id_)
    added_task.completedDate = datetime.date.today()
    cache.EditTasks([added_task])
    after_complete_size = len(cache)
    if complete_in_cache:
        assert after_complete_size == before_add_size + 1
        next(t for t in cache if t.id_ == added_task.id_)
    else:
        assert after_complete_size == before_add_size
        with pytest.raises(StopIteration):
            next(t for t in cache if t.id_ == added_task.id_)


def test_cache_preserve_fields(cache):
    """Confirm fields not being edited are preserved in cache."""
    comp = cache.comp
    task_to_add = Task(title=str(uuid4()),
                       completedDate=datetime.date.today()
                       if comp == 1 else None,
                       meta="foo")
    added_task = cache.AddTasks([task_to_add])[0]
    cache.EditTasks([Task(id_=added_task.id_, note="bar")])
    cached_task = cache.GetTasks(id_=added_task.id_, comp=comp)[0]
    assert cached_task.meta == "foo"
