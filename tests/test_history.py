# pylint: disable=protected-access

def test_history(toodledo):
    toodledo._session.toodledo_history_count = 1
    toodledo.GetAccount()
    history = toodledo._history
    assert len(history) == 1
    toodledo.GetTasks()
    assert len(history) == 1
    assert history[0][1].endswith('tasks/get.php')
