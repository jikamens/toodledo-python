import datetime
import logging
import os
import pickle


class TaskCache:
    """Automatically maintained local cache of tasks in a Toodledo account.

    A loaded task cache can be treated as a read-only list to access the tasks
    in the cache. Modifying objects in the cache directly will NOT update tasks
    in Toodledo or the cache on disk. To do that, you need to use the cache's
    EditTasks method.

    Behavior is completely undefined if you update the cache or edit while
    iterating over the cache.

    Properties:
    last_update -- List of updated tasks fetched in the last update
    last_delete -- List of deleted tasks fetched in the last update
    """
    def __init__(self, toodledo, path, update=True, autosave=True, comp=None,
                 fields=''):
        """Initialize a new TaskCache object.

        Required arguments:
        toodledo -- Instantiated API object
        path -- path on disk where the cache is stored

        Keyword arguments:
        update -- update cache automatically now (default: True)
        autosave -- save cache automatically when modified (default: True)
        comp -- (int) 0 to cache only uncompleted tasks, 1 for only completed
                tasks
        fields -- (string) optional fields to fetch and cache as per API
                  documentation

        If you change the values of the keyword arguments between
        instantiations of the same cache, then newly fetched tasks will reflect
        the new values but previously cached tasks will not.
        """
        self.logger = logging.getLogger(__name__)
        self.path = path
        self.autosave = autosave
        self.toodledo = toodledo
        if comp is not None and comp != 0 and comp != 1:
            raise ValueError(f'"comp" should be 0 or 1, not "{comp}"')
        self.comp = comp
        self.fields = fields
        if os.path.exists(path):
            self.load_from_path()
        else:
            self._new_cache()
        if update:
            self.update()

    def save(self):
        """Save the cache to disk."""
        self.dump_to_path()

    def load_from_path(self, path=None):
        """Load the cache from a file path.

        Keyword arguments:
        path -- path to use instead of the one specified on initialziation
        """
        path = path or self.path
        with open(path, 'rb') as f:
            self.cache = pickle.load(f)
        self.logger.debug(
            'Loaded %d tasks from {path}', len(self.cache['tasks']))

    def dump_to_path(self, path=None):
        """Dump the cache to a file path.

        Keyword arguments:
        path -- path to use instead of the one specified on initialziation
        """
        path = path or self.path
        with open(path, 'wb') as f:
            pickle.dump(self.cache, f)
        self.logger.debug('Dumped to %s', path)

    def _new_cache(self):
        cache = {}
        params = {}
        if self.comp is not None:
            params['comp'] = self.comp
        if self.fields:
            params['fields'] = self.fields
        cache['tasks'] = self.toodledo.GetTasks(params)
        if cache['tasks']:
            cache['newest'] = max(t.modified for t in cache['tasks'])
        else:
            cache['newest'] = datetime.datetime(1970, 1, 2)  # So we can -1 it
        self.cache = cache
        self.logger.debug('Initialized new (newest: %s)', cache['newest'])
        if self.autosave:
            self.save()

    def update(self):
        """Fetch updates from Toodledo."""
        # N.B. We fetch all tasks even if `comp` is set because otherwise we
        # won't know about tasks that have been completed or uncompleted.
        # - 1 to avoid race conditions
        after = self.cache['newest'].timestamp() - 1
        mapped = {t.id_: t for t in self}
        deleted_tasks = self.toodledo.GetDeletedTasks(after)
        delete_count = 0
        for t in deleted_tasks:
            if t.id_ in mapped:
                del mapped[t.id_]
                delete_count += 1
        if deleted_tasks:
            newest = max(t.stamp for t in deleted_tasks)
            new_newest = max(self.cache['newest'], newest)
            self.logger.debug('newest from deleted newest=%s, newest from '
                              'cache=%s, new newest=%s',
                              newest, self.cache['newest'], new_newest)
            self.cache['newest'] = new_newest
        self.logger.debug('Fetched %d deleted tasks, removed %d from cache',
                          deleted_tasks, delete_count)
        params = {'after': after}
        if self.fields:
            params['fields'] = self.fields
        updated_tasks = self.toodledo.GetTasks(params)
        comp_count = 0
        update_count = 0
        for t in updated_tasks:
            if self.comp == 0 and t.IsComplete():
                if t.id_ in mapped:
                    del mapped[t.id_]
                    comp_count += 1
            elif self.comp and not t.IsComplete():
                if t.id_ in mapped:
                    del mapped[t.id_]
                    comp_count += 1
            else:
                mapped[t.id_] = t
                update_count += 1
        if updated_tasks:
            newest = max(t.modified for t in updated_tasks)
            new_newest = max(self.cache['newest'], newest)
            self.logger.debug('newest from updated newest=%s, newest from '
                              'cache=%s, new newest=%s',
                              newest, self.cache['newest'], new_newest)
            self.cache['newest'] = new_newest
            self.logger.debug('Fetched %d updated tasks, ignored %d because '
                              'comp=%d, updated %d in cache',
                              len(updated_tasks), comp_count, self.comp,
                              update_count)
        self.cache['tasks'] = list(mapped.values())
        if self.autosave:
            self.save()
        self.last_update = updated_tasks
        self.last_delete = deleted_tasks

    def AddTasks(self, tasks):
        """Add the specified tasks and update the cache to reflect them."""
        self.toodledo.AddTasks(tasks)
        self.update()

    def EditTasks(self, tasks):
        """Edit the specified tasks and update the cache to reflect them."""
        self.toodledo.EditTasks(tasks)
        self.update()

    def DeleteTasks(self, tasks):
        """Delete the specified tasks and update the cache to reflect them."""
        self.toodledo.DeleteTasks(tasks)
        self.update()

    def __getitem__(self, item):
        return self.cache['tasks'][item]

    def __len__(self):
        return len(self.cache['tasks'])

    def __repr__(self):
        return (f'<TaskCache ({len(self.cache["tasks"])} items, '
                f'newest {str(self["cache"]["newest"])})>')
