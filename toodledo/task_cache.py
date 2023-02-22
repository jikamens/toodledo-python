from contextlib import contextmanager
import datetime
import logging
import os
import pickle

from toodledo.types import DueDateModifier, Priority, Status
from toodledo.task import _TaskSchema, Task


class TaskCache:
    """Automatically maintained local cache of tasks in a Toodledo account.

    A loaded task cache can be treated as a read-only list to access the tasks
    in the cache. Modifying objects in the cache directly will NOT update tasks
    in Toodledo or the cache on disk. To do that, you need to use the cache's
    AddTasks, EditTasks, and DeleteTasks methods.

    Behavior is completely undefined if you update the cache or edit while
    iterating over the cache.

    This function has all the same methods as the `Toodledo` session class, so
    you can use it as a drop-in replacement. And vice versa... The session
    class has a bunch of no-op functions (e.g., `save()`, `update()` so code
    written to use the cache will work fine using the session cache directory,
    just a bit slower.

    The cache updates automatically when you instantiate it unless you specify
    `update=False`. After that, any changes you make through the cache object
    are reflected in the cache, but changes made by someone else aren't until
    you call `update()` on the cache object.

    Call `save()` on the cache object to write it to disk. This happens
    automatically when you call `update()` unless you specify `autosave=False`
    when instantiating the cache.

    if you specify `comp=0` or `comp=1` when instantiating the cache, then
    you can use the `caching_everything()` context manager on the cache object
    to temporarily cache all newly completed or incompleted tasks. When the
    context exits, any tasks in the cache that don't match your persistent
    `comp` setting are removed from the cache. Using the cache this way is
    encouraged, because anyone who has been on Toodledo for a long time
    probably has many completed tasks, and you probably don't care about most
    of them most of the time in your code, so `comp=0` is probably the right
    way to use the cache most of the time.

    The `Toodledo` session class has a no-op `caching_everything()`
    context manager to preserve the ability to use the session and
    cache objects interchangeably.
    """
    schema = _TaskSchema()
    fields_map = {f.data_key or k: k for k, f in schema.fields.items()}

    def __init__(self, toodledo, path,  # pylint: disable=too-many-branches
                 update=True, autosave=True, comp=None, fields=''):
        """Initialize a new TaskCache object.

        Required arguments:
        toodledo -- Instantiated API object
        path -- path on disk where the cache is stored

        Keyword arguments:
        update -- update cache automatically now (default: True)
        autosave -- save cache automatically when updated (default: True)
        comp -- (int) 0 to cache only uncompleted tasks, 1 for only completed
                tasks
        fields -- (string) optional fields to fetch and cache as per API
                  documentation

        If you change the values of the keyword arguments between
        instantiations of the same cache, then newly fetched tasks will reflect
        the new values but previously cached tasks will not.
        """
        # If this is true then every time GetTasks is called, before it returns
        # its response it calls GetTasks on the server with the same parameters
        # and confirms that what it gets back matches what was retrieved from
        # the cache. This is used by the unit tests; it makes them run more
        # slowly but does a good job of validating cache integrity.
        self._paranoid = False
        self.logger = logging.getLogger(__name__)
        self.path = path
        self.autosave = autosave
        self.toodledo = toodledo
        if comp is not None and comp != 0 and comp != 1:
            raise ValueError(f'"comp" should be 0 or 1, not "{comp}"')
        self.comp = comp
        if self.comp is not None and self.comp not in (0, 1):
            raise ValueError(f'comp must be 0 or 1, not "{self.comp}')
        self.fields = fields
        if self.fields:
            self._check_fields(self.fields)
        if not os.path.exists(path):
            self._new_cache()
            return
        self.load_from_path()
        if self.cache.get('version', None) is None:
            self.cache['version'] = 1
        if self.cache['version'] < 2:
            self.cache['comp'] = self.comp
            self.cache['fields'] = self.fields
            self.cache['version'] = 2
        if self.cache['version'] < 3:
            self.cache['newest_delete'] = self.cache['newest']
            self.cache['version'] = 3
        if self.cache['version'] < 4:
            if not self.cache['fields'] or \
               'repeat' not in self.cache['fields'].split(','):
                self.logger.warning(
                    'Saved cache incompatible with current code; '
                    'reloading cache')
                self._new_cache()
                return
        if self.cache['comp'] != self.comp:
            if self.cache['comp'] is not None:
                raise ValueError(
                    f"Can't specify comp={self.comp} after previously "
                    f"specifying comp={self.cache['comp']}")
            # Safe to downgrade cache
            self.cache['comp'] = self.comp
        if not self.fields:
            self.fields = 'repeat'
        elif 'repeat' not in self.fields.split('.'):
            self.fields = 'repeat,' + self.fields
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

    @contextmanager
    def caching_everything(self):
        old_comp = self.comp
        try:
            if self.comp is not None:
                self.comp = None
            yield
            if old_comp is not None:
                self.cache['tasks'] = [
                    t for t in self.cache['tasks']
                    if (getattr(t, 'completedDate', None) and
                        old_comp == 1) or
                    (not getattr(t, 'completedDate', None) and
                     old_comp == 0)]
        finally:
            self.comp = old_comp

    def _new_cache(self):
        cache = {}
        params = {}
        if self.comp is not None:
            params['comp'] = self.comp
        if not self.fields:
            self.fields = 'repeat'
        elif 'repeat' not in self.fields.split(','):
            self.fields = 'repeat,' + self.fields
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
        cache['version'] = 4
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
        want_fields = params.get('fields', None)
        want_fields = want_fields.split(',') if want_fields else []
        want_fields = [self.fields_map[f] for f in want_fields]
        filter_fields = self._missing_fields(
            self.cache['fields'],
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
            if filter_fields or want_fields:
                task = Task(**task.__dict__)
            if filter_fields:
                for f in filter_fields:
                    try:
                        delattr(task, f)
                    except AttributeError:
                        pass
            for field in want_fields:
                setattr(task, field, getattr(task, field, None))
            yield task

    def GetTasks(self, params=None,  # pylint: disable=too-many-branches
                 before=None, after=None, comp=None, id_=None, fields=None):
        """See Toodledo.GetTasks."""
        if params is None:
            params = {}
        if before:
            params['before'] = before
        if after:
            params['after'] = after
        if comp is not None:
            params['comp'] = comp
        if id_:
            params['id'] = id_
        if fields:
            params['fields'] = fields
        filter_params = params.copy()
        comp = params.get('comp', None)
        if self.comp is not None and self.comp != comp:
            raise ValueError(f"Can't specify comp={comp} to cache created "
                             f"with comp={self.comp}")
        if 'before' in params:
            if isinstance(params['before'], datetime.datetime):
                params['before'] = params['before'].timestamp()
            else:
                filter_params['before'] = datetime.datetime.utcfromtimestamp(
                    params['before']).replace(tzinfo=datetime.timezone.utc)
        if 'after' in params:
            if isinstance(params['after'], datetime.datetime):
                params['after'] = params['after'].timestamp()
            else:
                filter_params['after'] = datetime.datetime.utcfromtimestamp(
                    params['after']).replace(tzinfo=datetime.timezone.utc)
        if params.get('fields', None):
            self._check_fields(params['fields'])
            missing_fields = self._missing_fields(params['fields'])
            if missing_fields:
                raise ValueError(
                    f'Requested fields {missing_fields} are not in cache')
        from_cache = list(self._filter_tasks(filter_params))
        if self._paranoid:
            from_toodledo = self.toodledo.GetTasks(params)
            from_cache.sort(key=lambda t: t.id_)
            from_toodledo.sort(key=lambda t: t.id_)
            assert len(from_cache) == len(from_toodledo)
            for i, t in enumerate(from_cache):
                t1 = t.__dict__.copy()
                t2 = from_toodledo[i].__dict__.copy()
                if t1.get('tags', None):
                    t1['tags'].sort()
                if t2.get('tags', None):
                    t2['tags'].sort()
                # Server is not always consistent
                del t1['modified']
                del t2['modified']
                assert t1 == t2
        return from_cache

    def GetDeletedTasks(self, after, update_cache=True):
        """Get tasks deleted after the specified timestamp.

        Required arguments:
        after -- Timestamp to start at

        Keyword arguments:
        update_cache -- Whether to remove tasks on the list from the cache and
          update the cache's idea of when we last fetched deleted tasks
          (default: True)
        """
        deleted_tasks = self.toodledo.GetDeletedTasks(after)
        if update_cache:
            deleted_ids = [t.id_ for t in deleted_tasks]
            self.cache['tasks'] = [t for t in self.cache['tasks']
                                   if t.id_ not in deleted_ids]
            self.cache['newest_delete'] = max(t.stamp for t in deleted_tasks)
        return deleted_tasks

    def AddTasks(self, tasks):
        """Add the specified tasks and update the cache to reflect them."""
        added_tasks = self.toodledo.AddTasks(tasks)
        # Copy so we can modify
        tasks = [Task(**task.__dict__) for task in tasks]
        split_fields = self.fields.split(',')
        for i, t in enumerate(tasks):
            # Update from fields returned by server
            t.__dict__.update(added_tasks[i].__dict__)
            # Default values
            if 'duedatemod' in split_fields and \
               getattr(t, 'dueDateModifier', None) is None:
                t.dueDateModifier = DueDateModifier.DUE_BY
            if 'length' in split_fields and getattr(t, 'length', None) is None:
                t.length = 0
            if 'note' in split_fields and getattr(t, 'note', None) is None:
                t.note = ''
            if 'priority' in split_fields and \
               getattr(t, 'priority', None) is None:
                t.priority = Priority.LOW
            if 'repeat' in split_fields and getattr(t, 'repeat', None) is None:
                t.repeat = ''
            if 'star' in split_fields and getattr(t, 'star', None) is None:
                t.star = False
            if 'status' in split_fields and getattr(t, 'status', None) is None:
                t.status = Status.NONE
            if 'tag' in split_fields and getattr(t, 'tags', None) is None:
                t.tags = []
        self.cache['tasks'].extend(
            t for t in tasks
            if self.comp is None or
            self.comp == 0 and not getattr(t, 'completedDate', None) or
            self.comp == 1 and getattr(t, 'completedDate', None))
        return added_tasks

    def EditTasks(self, tasks):
        """Edit the specified tasks and update the cache to reflect them.

        See Toodledo.EditTasks for more information."""
        #
        # The most complicated logic in this function is that we have to handle
        # tasks that are rescheduled by the server. That means:
        # * Detect when task are going to be rescheduled by the server because
        #   they're completedDate is being modified and reschedule=1 is set in
        #   them.
        # * Remove the reschedule=1 flag from edited tasks before putting them
        #   in the cache or returning them to the user.
        # * For tasks that were rescheduled, if comp is None or 1 then we need
        #   to find the newly completed tasks created automatically by the
        #   server and add them to the cache.
        #
        cache_map = {t.id_: t for t in self.cache['tasks']}
        rescheduling = (self.comp is None or self.comp == 1) and \
            any(True for t in tasks
                if getattr(t, 'reschedule', False) and
                getattr(t, 'completedDate', None) and
                (getattr(t, 'repeat', None) or
                 getattr(t, 'repeat', 'missing') == 'missing') and
                t.id_ in cache_map and
                getattr(cache_map[t.id_], 'repeat') and
                not getattr(cache_map[t.id_], 'completedDate', None))
        if rescheduling:
            # So we can use lastEditTask to fetch auto-created completed
            # clones of rescheduled tasks.
            account = self.toodledo.GetAccount()

        edited_tasks = self.toodledo.EditTasks(tasks)
        # Copy so we can modify
        tasks = [Task(**task.__dict__) for task in tasks]

        for t in tasks:
            try:
                delattr(t, 'reschedule')
            except AttributeError:
                pass

        # Update from fields returned by server
        for i, t in enumerate(tasks):
            t.__dict__.update(edited_tasks[i].__dict__)
        # Figure out which tasks to update in cache and which to remove
        if self.comp is None:
            wanted = tasks
            unwanted = []
        else:
            incomplete = []
            complete = []
            for t in tasks:
                (complete if getattr(t, 'completedDate', None)
                 else incomplete).append(t)
            wanted = incomplete if self.comp == 0 else complete
            unwanted = complete if self.comp == 1 else incomplete
        # Remove unwanted tasks
        for t in unwanted:
            cache_map.pop(t.id_, None)
        # Update wanted tasks
        for t in wanted:
            cache_map[t.id_] = t

        # Handle rescheduled tasks
        if rescheduling:
            completed_tasks = self.toodledo.GetTasks(
                comp=1, fields=self.fields, after=account.lastEditTask)
            for t in completed_tasks:
                cache_map[t.id_] = t

        self.cache['tasks'] = list(cache_map.values())

        return edited_tasks

    def DeleteTasks(self, tasks):
        """Delete the specified tasks and update the cache to reflect them."""
        self.toodledo.DeleteTasks(tasks)
        deleted_ids = [t.id_ for t in tasks]
        self.cache['tasks'] = [t for t in self.cache['tasks']
                               if t.id_ not in deleted_ids]

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
