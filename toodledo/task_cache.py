import datetime
import logging
import os
import pickle

from toodledo.task import _TaskSchema, Task


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
    schema = _TaskSchema()
    fields_map = {f.data_key or k: k for k, f in schema.fields.items()}

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
        if self.fields:
            self._check_fields(self.fields)
        if os.path.exists(path):
            self.load_from_path()
        else:
            self._new_cache()
        if self.cache.get('version', None) is None:
            self.cache['version'] = 1
        if self.cache['version'] < 2:
            self.cache['comp'] = self.comp
            self.cache['fields'] = self.fields
            self.cache['version'] = 2
        if self.cache['version'] < 3:
            self.cache['newest_delete'] = self.cache['newest']
            self.cache['version'] = 3
        if self.cache['comp'] != self.comp:
            if self.cache['comp'] is not None:
                raise ValueError(
                    f"Can't specify comp={self.comp} after previously "
                    f"specifying comp={self.cache['comp']}")
            # Safe to downgrade cache
            self.cache['comp'] = self.comp
        if self.cache['fields'] != self.fields:
            missing = self._missing_fields(self.fields)
            if missing:
                raise ValueError(
                    f"Can't initialize cache with fields {missing} "
                    f"that weren't requested when cache was created")
            # Safe to downgrade fields
            self.cache['fields'] = self.fields
        if update:
            self.update()

    def _missing_fields(self, want_fields, cache_fields=None):
        if cache_fields is None:
            cache_fields = self.cache['fields']
        cache_fields = (cache_fields.split(',') if cache_fields else [])
        want_fields = (want_fields.split(',') if want_fields else [])
        return sorted(set(want_fields) - set(cache_fields))

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
            cache['newest'] = datetime.datetime(1970, 1, 2,  # So we can -1 it
                                                tzinfo=datetime.timezone.utc)
        cache['newest_delete'] = datetime.datetime(
            1970, 1, 2, tzinfo=datetime.timezone.utc)
        cache['comp'] = self.comp
        cache['fields'] = self.fields
        cache['version'] = 3
        self.cache = cache
        self.logger.debug('Initialized new (newest: %s)', cache['newest'])
        if self.autosave:
            self.save()

    def update(self):
        """Fetch updates from Toodledo."""
        # N.B. We fetch all tasks even if `comp` is set because otherwise we
        # won't know about tasks that have been completed or uncompleted.
        # - 1 to avoid race conditions
        after = self.cache['newest_delete'].timestamp() - 1
        mapped = {t.id_: t for t in self}
        deleted_tasks = self.toodledo.GetDeletedTasks(after)
        delete_count = 0
        for t in deleted_tasks:
            if t.id_ in mapped:
                del mapped[t.id_]
                delete_count += 1
        if deleted_tasks:
            self.cache['newest_delete'] = max(t.stamp for t in deleted_tasks)

            self.logger.debug('new newest delete=%s',
                              self.cache['newest_delete'])
        self.logger.debug('Fetched %d deleted tasks, removed %d from cache',
                          deleted_tasks, delete_count)
        after = self.cache['newest'].timestamp() - 1
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
            self.cache['newest'] = max(t.modified for t in updated_tasks)
            self.logger.debug('new newest=%s', self.cache['newest'])
            self.logger.debug('Fetched %d updated tasks, ignored %d because '
                              'comp=%d, updated %d in cache',
                              len(updated_tasks), comp_count, self.comp,
                              update_count)
        self.cache['tasks'] = list(mapped.values())
        if self.autosave:
            self.save()
        self.last_update = updated_tasks
        self.last_delete = deleted_tasks

    def _check_fields(self, fields):
        if not fields:
            return
        fields = fields.split(',')
        missing = sorted(f for f in fields if f not in self.fields_map)
        if missing:
            raise ValueError(
                f"Fields not supported by this library: {missing}")

    def _filter_tasks(self, params):
        params = params.copy()
        filter_fields = self._missing_fields(
            self.cache.get('fields', None) or '',
            params.get('fields', None) or '')
        filter_fields = [self.fields_map[f] for f in filter_fields]
        for task in self:
            if 'id' in params:
                if task.id_ == params['id']:
                    yield [task]
                    return
                continue
            if params.get('comp', None) == 0 and task.completedDate:
                continue
            if params.get('comp', None) == 1 and not task.completedDate:
                continue
            if 'before' in params and task.modified >= params['before']:
                continue
            if 'after' in params and task.modified <= params['after']:
                continue
            if filter_fields:
                task = Task(**task.__dict__)
                for f in filter_fields:
                    delattr(task, f)
            yield task

    def GetTasks(self, params):
        filter_params = params.copy()
        comp = params.get('comp', None)
        if self.comp is not None and self.comp != params['comp']:
            raise ValueError(f"Can't specify comp={comp} to cache created "
                             f"with comp={self.comp}")
        if 'before' in params:
            if isinstance(params['before'], datetime.datetime):
                params['before'] = params['before'].timestamp()
            else:
                filter_params['before'] = datetime.datetime.utcfromtimestamp(
                    params['before'])
        if 'after' in params:
            if isinstance(params['after'], datetime.datetime):
                params['after'] = params['after'].timestamp()
            else:
                filter_params['after'] = datetime.datetime.utcfromtimestamp(
                    params['after'])
        if params.get('fields', None):
            self._check_fields(params['fields'])
            missing_fields = self._missing_fields(params['fields'])
            if missing_fields:
                raise ValueError(
                    f'Requested fields {missing_fields} are not in cache')
        self.update()
        return list(self._filter_tasks(filter_params))

    def GetDeletedTasks(self, after):
        # We don't cache this.
        return self.toodledo.GetDeletedTasks(after)

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

    # Passthrough functions so that the cache object can be a drop-in
    # replacement for the session object.

    def GetFolders(self):
        return self.toodledo.GetFolders()

    def AddFolder(self, folder):
        return self.toodledo.AddFolder(folder)

    def DeleteFolder(self, folder):
        return self.toodledo.DeleteFolder(folder)

    def EditFolder(self, folder):
        return self.toodledo.EditFolder(folder)

    def GetContexts(self):
        return self.toodledo.GetContexts()

    def AddContext(self, context):
        return self.toodledo.AddContext(context)

    def DeleteContext(self, context):
        return self.toodledo.DeleteContext(context)

    def EditContext(self, context):
        return self.toodledo.EditContext(context)

    def GetAccount(self):
        account = self.toodledo.GetAccount()
        account.lastEditTask = self.cache['newest']
        account.latDeleteTask = self.cache['newest_delete']
        return account

    def __getitem__(self, item):
        return self.cache['tasks'][item]

    def __len__(self):
        return len(self.cache['tasks'])

    def __repr__(self):
        return (f'<TaskCache ({len(self.cache["tasks"])} items, '
                f'newest {str(self.cache["newest"])})>')
