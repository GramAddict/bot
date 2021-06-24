import argparse
from os import getcwd, path
from GramAddict.version import __version__
from GramAddict.core.download_from_github import download_from_github
from GramAddict.core.bot_flow import start_bot


def cmd_init(args):
    if args.account_name is not None:
        print(f"Script launched in {getcwd()}, files will be available there.")
        for username in args.account_name:
            if not path.exists("./run.py"):
                print("Creating run.py ...")
                download_from_github(
                    "https://github.com/GramAddict/bot/blob/master/run.py"
                )
            if not path.exists(f"./accounts/{username}"):
                print(
                    f"Creating 'accounts/{username}' folder with a config starting point inside. You have to edit these files according with https://docs.gramaddict.org/#/configuration"
                )
                download_from_github(
                    "https://github.com/GramAddict/bot/tree/master/config-examples",
                    output_dir=f"accounts/{username}",
                    flatten=True,
                )
            else:
                print(f"'accounts/{username}' folder already exists, skip.")
    else:
        print("You have to provide at last one account name..")


def cmd_run(args):
    start_bot()


_commands = [
    dict(
        action=cmd_init,
        command="init",
        help="creates your account folder under accounts with files for configuration",
        flags=[
            dict(
                args=["account_name"],
                nargs="+",
                help="instagram account name to initialize",
            ),
        ],
    ),
    dict(
        action=cmd_run,
        command="run",
        help="start the bot!",
        flags=[
            dict(args=["--config"], nargs="?", help="provide the config.yml path"),
        ],
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="GramAddict",
        description="free human-like Instagram bot",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} {__version__}"
    )
    subparser = parser.add_subparsers(dest="subparser")
    actions = {}
    for c in _commands:
        cmd_name = c["command"]
        actions[cmd_name] = c["action"]
        sp = subparser.add_parser(
            cmd_name,
            help=c.get("help"),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        for f in c.get("flags", []):
            args = f.get("args")
            if not args:
                args = ["-" * min(2, len(n)) + n for n in f["name"]]
            kwargs = f.copy()
            kwargs.pop("name", None)
            kwargs.pop("args", None)
            kwargs.pop("run", None)
            sp.add_argument(*args, **kwargs)

    args = parser.parse_args()

    if args.subparser:
        actions[args.subparser](args)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
