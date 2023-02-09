from toodledo import Task


def test_get_account(toodledo):
    _ = toodledo.GetAccount()


def test_get_tasks(toodledo):
    tasks = toodledo.GetTasks(params={})
    assert isinstance(tasks, list)


def test_get_tasks_with_known_folders(toodledo):
    folders = toodledo.GetFolders()
    privateFolderId = [f.id_ for f in folders
                       if f.name == "Test Folder - private"][0]
    publicFolderId = [f.id_ for f in folders if f.name == "Test Folder"][0]

    wanted_tasks = ([None, "Test task with private folder", privateFolderId],
                    [None, "Test task with public folder", publicFolderId])

    attempts = 0
    changed = True
    while changed and attempts < 2:
        changed = False
        attempts += 1
        tasks = toodledo.GetTasks(params={"fields": "folder"})
        for wanted in wanted_tasks:
            try:
                wanted[0] = next(t for t in tasks if t.title == wanted[1])
            except StopIteration:
                toodledo.AddTasks([Task(title=wanted[1], folderId=wanted[2])])
                changed = True

    for wanted in wanted_tasks:
        assert wanted[0].folderId == wanted[2]


def test_get_tasks_with_known_contexts(toodledo):
    contexts = toodledo.GetContexts()
    privateContextId = [
        x.id_ for x in contexts if x.name == "Test Context - private"][0]
    publicContextId = [
        x.id_ for x in contexts if x.name == "Test Context - public"][0]

    wanted_tasks = ([None, "Test task with private context", privateContextId],
                    [None, "Test task with public context", publicContextId])

    attempts = 0
    changed = True
    while changed and attempts < 2:
        changed = False
        attempts += 1
        tasks = toodledo.GetTasks(params={"fields": "context"})
        for wanted in wanted_tasks:
            try:
                wanted[0] = next(t for t in tasks if t.title == wanted[1])
            except StopIteration:
                toodledo.AddTasks([Task(title=wanted[1], contextId=wanted[2])])
                changed = True

    for wanted in wanted_tasks:
        assert wanted[0].contextId == wanted[2]
