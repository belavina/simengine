"""Record/Replay functionalities"""

import functools
from itertools import zip_longest
from datetime import datetime as dt
import time
import logging
import inspect


class Recorder:
    """Recorder can be used to record and replay methods or functions
    """

    def __init__(self):
        self._actions = []
        self._enabled = True
        self._replaying = False

    def __call__(self, work):
        """Make an instance of recorder a callable object that can be used as a decorator
        with functions/class methods.
        Function calls will be registered by the recorder & can be replayed later on.

        Example:
            recorder = Recorder()
            @recorder
            def my_action():
                ...

            each call to my_action() will be stored in action history of the recorder instance,
        """

        @functools.wraps(work)
        def record_wrapper(asset_self, *f_args, **f_kwargs):

            if (
                asset_self.__module__.startswith("enginecore.state.api")
                and self._enabled
            ):
                partial_func = functools.partial(work, asset_self, *f_args, **f_kwargs)
                self._actions.append(
                    {
                        "work": functools.update_wrapper(partial_func, work),
                        "time": dt.now(),
                    }
                )
            return work(asset_self, *f_args, **f_kwargs)

        return record_wrapper

    @property
    def enabled(self):
        """Recorder status indicating if it's accepting & recording new actions"""
        return self._enabled

    @property
    def replaying(self):
        """Recorder status indicating if recorder is in process of replaying actions"""
        return self._replaying

    @enabled.setter
    def enabled(self, value):
        if not self.replaying:
            self._enabled = value

    def get_action_details(self, slc=slice(None, None)):
        """Human-readable details on action history
        Args:
            slc(slice): range of actions to be returned
        Returns:
            list: history of actions
        """
        action_details = []

        for action in self._actions[slc]:

            wrk_asset = action["work"].args[0]
            if inspect.isclass(wrk_asset):
                obj_str = wrk_asset.__name__
            else:
                obj_str = "{asset}({key})".format(
                    asset=type(wrk_asset).__name__, key=wrk_asset.key
                )

            action_details.append(
                {
                    "work": "{obj}.{func}{args}".format(
                        obj=(obj_str),
                        func=action["work"].__name__,
                        args=action["work"].args[1:],
                    ),
                    "timestamp": int(action["time"].timestamp()),
                    "number": self._actions.index(action),
                }
            )

        return action_details

    def erase_all(self):
        """Clear all actions"""
        self.erase_range(slice(None, None))

    def erase_range(self, slc):
        """Delete a slice of actions
        Args:
            slc(slice): range of actions to be deleted
        """
        del self._actions[slc]

    def replay_all(self):
        """Replay all actions"""
        self.replay_range(slice(None, None))

    def replay_range(self, slc):
        """Replay a slice of actions
        Args:
            slc(slice): range of actions to be performed
        """

        pre_replay_enabled_status = self.enabled
        self.enabled = False
        self._replaying = True

        for action, next_action in self.actions_iter(self._actions, slc):

            action_info = "Replaying: [ {action}{args} ]".format(
                action=action["work"].__name__, args=action["work"].args
            )

            logging.info(action_info)
            # perform action
            action["work"]()

            # simulate pause between 2 actions
            if next_action:
                next_delay = (next_action["time"] - action["time"]).seconds
                logging.info("Paused for %s seconds...", next_delay)
                time.sleep(next_delay)

        self._replaying = False
        self.enabled = pre_replay_enabled_status

    @classmethod
    def actions_iter(cls, actions, slc):
        """Get an iterator yielding current & next actions
        Args:
            actions(list): action history
            slc(slice): range of actions
        Returns:
            iterator: aggragates actions & actions+1 in one iter
        """
        return zip_longest(actions[slc], actions[slc][1:])

    @classmethod
    def perform_dry_run(cls, actions, slc):
        """Perform replay dry run by outputting step-by-step actions (without executing them)
        Args:
            actions(list): action history, must contain action "number", "work" (action itself) & "timestamp"
            slc(slice): range of actions
        """

        for action, next_action in cls.actions_iter(actions, slc):

            print("{number}) [executing]: {work}".format(**action))
            out_pad = len("{number}) ".format(**action)) * " "

            if next_action:
                next_delay = (
                    dt.fromtimestamp(next_action["timestamp"])
                    - dt.fromtimestamp(action["timestamp"])
                ).seconds

                print(
                    "{pad}[sleeping]:  {sleep} seconds".format(
                        pad=out_pad, sleep=next_delay
                    )
                )

                for _ in range(1, next_delay + 1):
                    print("{pad}.".format(pad=out_pad))
                    time.sleep(1)


RECORDER = Recorder()
