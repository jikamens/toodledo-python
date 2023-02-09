from uuid import uuid4

from toodledo import Folder


# There's no export for these in the toodledo web interface so the user will
# have to make them themselves
def test_get_known_folders(toodledo):
    wanted_folders = ([None, "Test Folder", False, False],
                      [None, "Test Folder - archived", True, False],
                      [None, "Test Folder - private", False, True])

    attempts = 0
    changed = True
    while changed and attempts < 2:
        changed = False
        attempts += 1
        folders = toodledo.GetFolders()
        for wanted in wanted_folders:
            try:
                wanted[0] = next(f for f in folders if f.name == wanted[1])
            except StopIteration:
                newFolder = toodledo.AddFolder(
                    Folder(name=wanted[1], archived=wanted[2],
                           private=wanted[3]))
                if wanted[2]:
                    newFolder.archived = True
                    toodledo.EditFolder(newFolder)
                changed = True

    assert isinstance(folders, list)
    assert len(folders) >= 3

    orders = set()
    for wanted in wanted_folders:
        folder = next(f for f in folders if f.name == wanted[1])
        assert folder.archived is wanted[2]
        assert folder.private is wanted[3]
        orders.add(folder.order)

    assert len(orders) == len(wanted_folders)


def test_add_edit_delete_folder(toodledo):
    randomName = str(uuid4())
    newFolder = toodledo.AddFolder(Folder(name=randomName, private=False))
    assert isinstance(newFolder, Folder)
    assert newFolder.name == randomName
    assert newFolder.private is False
    assert newFolder.archived is False

    newFolder.name = str(uuid4())
    newFolder.private = True
    newFolder.archived = True

    editedFolder = toodledo.EditFolder(newFolder)
    assert isinstance(editedFolder, Folder)
    assert editedFolder.id_ == newFolder.id_
    assert editedFolder.name == newFolder.name

    assert editedFolder.private == newFolder.private
    assert editedFolder.archived == newFolder.archived

    allFolders = toodledo.GetFolders()
    ourFolder = [f for f in allFolders if f.id_ == newFolder.id_][0]
    assert ourFolder.id_ == newFolder.id_
    assert ourFolder.name == newFolder.name

    assert ourFolder.private == newFolder.private
    assert ourFolder.archived == newFolder.archived

    toodledo.DeleteFolder(editedFolder)
