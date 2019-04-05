"""CLI endpoints for replaying, listing and managing recorded actions
"""
import argparse
import sys
import os
from datetime import datetime as dt
from enginecore.state.net.state_client import StateClient
from enginecore.tools.recorder import Recorder


def print_action_list(action_details):
    """Display action history"""

    if not action_details:
        print("Action history is empty or the range specifier is invalid!")
        return

    for action in action_details:
        print(
            "{number}) [{time}] {work}".format(
                **action, time=dt.fromtimestamp(action["timestamp"])
            )
        )


def dry_run_actions(args):
    """Do a dry run of action replay without changing of affecting assets' states"""
    action_slc = slice(args["start"], args["end"])
    action_details = StateClient.list_actions(action_slc)
    try:
        Recorder.perform_dry_run(action_details, action_slc)
    except KeyboardInterrupt:
        print("Dry-run was interrupted by the user", file=sys.stderr)


def range_args():
    """Get common action arguments"""

    common_args = argparse.ArgumentParser(add_help=False)

    common_args.add_argument(
        "-s",
        "--start",
        type=int,
        help="Starting at this action number (range specifier)",
    )

    common_args.add_argument(
        "-e", "--end", type=int, help="Ending at this action number (range specifier)"
    )

    return common_args


def handle_file_command(args, client_request_func):
    """Process file command (either save or load)
    Args:
        client_request_func(callable): StateClient method processing file command
    """
    client_request_func(
        os.path.abspath(os.path.expanduser(args["filename"])),
        slice(args["start"], args["end"]),
    )


def actions_command(actions_group):
    """Action command can be used to manage/replay recorded actions performed by SimEngine users"""

    play_subp = actions_group.add_subparsers()

    # replay commands
    replay_action = play_subp.add_parser(
        "replay",
        help="Replay actions, will replay all history if range is not provided",
        parents=[range_args()],
    )
    replay_action.add_argument(
        "-l", "--list", action="store_true", help="List re-played actions"
    )

    #  clear action history
    clear_action = play_subp.add_parser(
        "clear", help="Purge action history", parents=[range_args()]
    )
    clear_action.add_argument(
        "-l", "--list", action="store_true", help="List deleted actions"
    )

    # misc
    disable_action = play_subp.add_parser(
        "disable", help="Disable recorder (recorder will ignore incoming commands)"
    )
    enable_action = play_subp.add_parser(
        "enable", help="Enable recorder registering incoming actions"
    )
    status_action = play_subp.add_parser(
        "status",
        help="Returns recorder status indicating if recorder is enabled and if it is in-process of replaying",
    )
    list_action = play_subp.add_parser(
        "list", help="List action history", parents=[range_args()]
    )
    dry_run_action = play_subp.add_parser(
        "dry-run", help="Perform a dry run of actions replay", parents=[range_args()]
    )

    save_action = play_subp.add_parser(
        "save", help="Save action history to a file", parents=[range_args()]
    )

    save_action.add_argument(
        "-l", "--list", action="store_true", help="Explicitly list saved actions"
    )

    save_action.add_argument(
        "-f", "--filename", type=str, required=True, help="Target file name"
    )

    load_action = play_subp.add_parser(
        "load",
        help="Load action history from a file (will override the existing actions)",
        parents=[range_args()],
    )

    load_action.add_argument(
        "-f", "--filename", type=str, required=True, help="Will load from this file"
    )

    rand_action = play_subp.add_parser(
        "random", help="Perform random actions associated with assets"
    )
    rand_action.add_argument(
        "-c", "--count", type=int, help="Number of actions to be performed", default=1
    )
    rand_action.add_argument(
        "-s",
        "--seconds",
        type=int,
        help="Perform actions for 'n' seconds (alternative to 'count')",
    )
    rand_action.add_argument(
        "-n", "--nap-time", type=int, help="Pause between each random action"
    )

    # cli actions/callbacks
    replay_action.set_defaults(
        func=lambda args: [
            print_action_list(
                StateClient.list_actions(slice(args["start"], args["end"]))
            )
            if args["list"]
            else None,
            StateClient.replay_actions(slice(args["start"], args["end"])),
        ]
    )

    clear_action.set_defaults(
        func=lambda args: [
            print_action_list(
                StateClient.list_actions(slice(args["start"], args["end"]))
            )
            if args["list"]
            else None,
            StateClient.clear_actions(slice(args["start"], args["end"])),
        ]
    )

    list_action.set_defaults(
        func=lambda args: print_action_list(
            StateClient.list_actions(slice(args["start"], args["end"]))
        )
    )

    disable_action.set_defaults(
        func=lambda _: StateClient.set_recorder_status(enabled=False)
    )

    enable_action.set_defaults(
        func=lambda _: StateClient.set_recorder_status(enabled=True)
    )
    status_action.set_defaults(
        func=lambda _: print(
            "Enabled: {enabled}\nReplaying: {replaying}".format(
                **StateClient.get_recorder_status()
            )
        )
    )
    dry_run_action.set_defaults(func=dry_run_actions)

    save_action.set_defaults(
        func=lambda args: handle_file_command(args, StateClient.save_actions)
    )
    load_action.set_defaults(
        func=lambda args: handle_file_command(args, StateClient.load_actions)
    )

    rand_action.set_defaults(func=StateClient.rand_actions)