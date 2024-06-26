from uuid import uuid4

from toodledo import Context


# There's no export for these in the toodledo web interface so the user will
# have to make them themselves
def test_get_known_contexts(toodledo):
    contexts = toodledo.GetContexts()
    changed = False
    wanted_contexts = (("Test Context - private", True),
                       ("Test Context - public", False))
    for wanted in wanted_contexts:
        if not any(True for c in contexts if c.name == wanted[0]):
            toodledo.AddContext(Context(name=wanted[0], private=wanted[1]))
            changed = True
    if changed:
        contexts = toodledo.GetContexts()

    assert isinstance(contexts, list)
    assert len(contexts) >= 2

    for wanted in wanted_contexts:
        context = next(c for c in contexts if c.name == wanted[0])
        assert context.private is wanted[1]


def test_add_edit_delete_folder(toodledo):
    randomName = str(uuid4())
    newContext = toodledo.AddContext(Context(name=randomName, private=False))
    assert isinstance(newContext, Context)
    assert newContext.name == randomName
    assert newContext.private is False

    newContext.name = str(uuid4())
    newContext.private = True

    editedContext = toodledo.EditContext(newContext)
    assert isinstance(editedContext, Context)
    assert editedContext.id_ == newContext.id_
    assert editedContext.name == newContext.name

    assert editedContext.private == newContext.private

    allContexts = toodledo.GetContexts()
    ourContext = [x for x in allContexts if x.id_ == newContext.id_][0]
    assert ourContext.id_ == newContext.id_
    assert ourContext.name == newContext.name

    assert ourContext.private == newContext.private

    toodledo.DeleteContext(editedContext)
